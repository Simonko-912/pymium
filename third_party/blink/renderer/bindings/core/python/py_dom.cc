// Copyright 2026 The Pymium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Value marshalling + the two live-proxy types that let Python hold Blink
// objects. Struct layout is pinned in py_dom.h; this TU is where the
// PyTypeObject v-tables live. The header is small precisely so a security
// review covers the whole surface in one sitting (ARCHITECTURE.md 3.3).

#include "third_party/blink/renderer/bindings/core/python/py_dom.h"

#include <Python.h>

#include "third_party/blink/renderer/platform/wtf/text/wtf_string.h"
#include "v8/include/v8.h"

namespace blink {
namespace {

PythonDomTarget* PythonDomTarget_New(v8::Isolate* isolate) {
  PythonDomTarget* target = new PythonDomTarget();
  target->isolate = isolate;
  return target;
}

void PythonDomTarget_Reset(PythonDomTarget* target) {
  if (!target)
    return;
  target->target_handle.Reset();
  target->context_handle.Reset();
  target->isolate = nullptr;
}

// --- PyDomObject ------------------------------------------------------------(
// A PyDomObject is the address of a PythonDomTarget plus a PyObject header.
// The v8::Global holds Blink's reference; Python's refcount just keeps
// this small proxy alive. No second copy of the DOM is ever made.

PyObject* PyDomObject_Create(PythonDomTarget* target) {
  if (!target) {
    PyErr_SetString(PyExc_RuntimeError, "null python dom target");
    return nullptr;
  }
  PyDomObject* self = PyObject_New(PyDomObject, &PyDomObject_Type);
  if (!self) {
    PythonDomTarget_Reset(target);
    delete target;
    return nullptr;
  }
  self->target_ = target;
  return reinterpret_cast<PyObject*>(self);
}

void PyDomObject_Dealloc(PyDomObject* self) {
  PythonDomTarget_Reset(self->target_);
  delete self->target_;
  self->target_ = nullptr;
  Py_TYPE(self)->tp_free(reinterpret_cast<PyObject*>(self));
}

PyObject* PyDomObject_GetAttr(PyObject* o, PyObject* name) {
  PyDomObject* self = reinterpret_cast<PyDomObject*>(o);
  const char* attribute = PyUnicode_AsUTF8(name);
  v8::Isolate* isolate = self->target_->isolate;
  v8::Local<v8::Context> context = self->target_->context_handle.Get(isolate);
  v8::Context::Scope context_scope(context);
  v8::HandleScope scope(isolate);

  v8::Local<v8::Value> value;
  if (!self->target_->target_handle.Get(isolate)
           ->Get(context, v8::String::NewFromUtf8(isolate, attribute)
                              .ToLocalChecked())
           .ToLocal(&value)) {
    PyErr_SetString(PyExc_AttributeError, attribute);
    return nullptr;
  }
  // Callable attributes return a bound PyDomMethod (a "live method proxy"),
  // anything else returns a marshalled scalar or another live proxy.
  if (value->IsFunction()) {
    PyDomMethod* method = PyObject_New(PyDomMethod, &PyDomMethod_Type);
    if (!method)
      return nullptr;
    method->self_ = Py_NewRef(o);
    method->name_ = Py_NewRef(name);
    return reinterpret_cast<PyObject*>(method);
  }
  return PyObject_FromV8(isolate, value, context);
}

// --- PyDomMethod ------------------------------------------------------------(
// index references the python_js.cc constructor so a Blink method exposed to
// Python is called through the same v8::Function each time.

PyObject* PyDomMethod_Call(PyDomMethod* self, PyObject* args, PyObject*) {
  PyDomObject* owner = reinterpret_cast<PyDomObject*>(self->self_);
  const char* attribute = PyUnicode_AsUTF8(self->name_);
  v8::Isolate* isolate = owner->target_->isolate;
  v8::Local<v8::Context> context = owner->target_->context_handle.Get(isolate);
  v8::Context::Scope context_scope(context);
  v8::HandleScope scope(isolate);

  v8::Local<v8::Value> function;
  if (!owner->target_->target_handle.Get(isolate)
           ->Get(context, v8::String::NewFromUtf8(isolate, attribute)
                              .ToLocalChecked())
           .ToLocal(&function) ||
      !function->IsFunction()) {
    PyErr_SetString(PyExc_AttributeError, attribute);
    return nullptr;
  }

  Py_ssize_t argc = PyTuple_GET_SIZE(args);
  std::vector<v8::Local<v8::Value>> argv;
  argv.reserve(argc);
  for (Py_ssize_t i = 0; i < argc; ++i) {
    v8::Local<v8::Value> converted =
        PyObject_ToV8(isolate, context, PyTuple_GET_ITEM(args, i));
    if (converted.IsEmpty())
      return nullptr;
    argv.push_back(converted);
  }

  v8::Local<v8::Value> result;
  if (!function.As<v8::Function>()
           ->Call(context, owner->target_->target_handle.Get(isolate),
                  static_cast<int>(argc), argv.data())
           .ToLocal(&result)) {
    PyErr_SetString(PyExc_RuntimeError, "v8 call failed");
    return nullptr;
  }
  return PyObject_FromV8(isolate, result, context);
}

void PyDomMethod_Dealloc(PyDomMethod* self) {
  Py_DECREF(self->self_);
  Py_DECREF(self->name_);
  Py_TYPE(self)->tp_free(reinterpret_cast<PyObject*>(self));
}

}  // namespace

// PyDomObject_Type -------------------------------------------------------------
PyTypeObject PyDomObject_Type = {
    PyVarObject_HEAD_INIT(nullptr, 0)
    "pymium._DomProxy",
    sizeof(PyDomObject),
    0,
    reinterpret_cast<destructor>(PyDomObject_Dealloc),
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    PyDomObject_GetAttr,
    0,
    0,
    0,
    0,
    0,
    0,
    Py_TPFLAGS_DEFAULT,
    "live proxy for a Blink DOM object seen from Python",
};

PyTypeObject PyDomMethod_Type = {
    PyVarObject_HEAD_INIT(nullptr, 0)
    "pymium._BoundMethod",
    sizeof(PyDomMethod),
    0,
    reinterpret_cast<destructor>(PyDomMethod_Dealloc),
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    Py_TPFLAGS_DEFAULT,
    "live v8 function bound to a PyDomObject proxy",
};

// Marshalling ---------------------------------------------------------------
PyObject* PyObject_FromV8(v8::Isolate* isolate,
                          const v8::Local<v8::Value>& value,
                          const v8::Local<v8::Context>& context) {
  v8::HandleScope handle_scope(isolate);
  if (value.IsEmpty() || value->IsNull() || value->IsUndefined())
    Py_RETURN_NONE;
  if (value->IsBoolean())
    return PyBool_FromLong(value.As<v8::Boolean>()->Value() ? 1 : 0);
  if (value->IsInt32())
    return PyLong_FromLong(value.As<v8::Int32>()->Value());
  if (value->IsUint32())
    return PyLong_FromUnsignedLong(value.As<v8::Uint32>()->Value());
  if (value->IsNumber())
    return PyFloat_FromDouble(value.As<v8::Number>()->Value());
  if (value->IsString()) {
    v8::String::Utf8Value utf8(isolate, value.As<v8::String>());
    return PyUnicode_FromStringAndSize(*utf8, utf8.length());
  }
  if (value->IsArray()) {
    v8::Local<v8::Array> array = value.As<v8::Array>();
    PyObject* list = PyList_New(array->Length());
    if (!list)
      return nullptr;
    for (uint32_t i = 0; i < array->Length(); ++i) {
      v8::Local<v8::Value> item;
      if (!array->Get(context, i).ToLocal(&item)) {
        Py_DECREF(list);
        return nullptr;
      }
      PyObject* item_py = PyObject_FromV8(isolate, item, context);
      if (!item_py) {
        Py_DECREF(list);
        return nullptr;
      }
      PyList_SET_ITEM(list, i, item_py);
    }
    return list;
  }
  if (value->IsObject() || value->IsFunction()) {
    PythonDomTarget* target = PythonDomTarget_New(isolate);
    target->target_handle.Reset(isolate, value.As<v8::Object>());
    target->context_handle.Reset(isolate, context);
    return PyDomObject_Create(target);
  }
  PyErr_SetString(PyExc_TypeError, "unsupported v8 value type");
  return nullptr;
}

v8::Local<v8::Value> PyObject_ToV8(v8::Isolate* isolate,
                                   const v8::Local<v8::Context>& context,
                                   PyObject* value) {
  v8::EscapableHandleScope handle_scope(isolate);
  if (!value || value == Py_None)
    return handle_scope.Escape(v8::Null(isolate));
  if (value == Py_True || value == Py_False)
    return handle_scope.Escape(
        v8::Boolean::New(isolate, value == Py_True));
  if (PyLong_Check(value))
    return handle_scope.Escape(
        v8::Integer::New(isolate, (int32_t)PyLong_AsLong(value)));
  if (PyFloat_Check(value))
    return handle_scope.Escape(
        v8::Number::New(isolate, PyFloat_AS_DOUBLE(value)));
  if (PyUnicode_Check(value)) {
    const char* utf8 = PyUnicode_AsUTF8(value);
    if (utf8)
      return handle_scope.Escape(
          v8::String::NewFromUtf8(isolate, utf8).ToLocalChecked());
  }
  if (PyList_Check(value)) {
    v8::Local<v8::Array> array =
        v8::Array::New(isolate, PyList_GET_SIZE(value));
    for (Py_ssize_t i = 0; i < PyList_GET_SIZE(value); ++i)
      array->Set(context, (uint32_t)i,
                 PyObject_ToV8(isolate, context, PyList_GET_ITEM(value, i)));
    return handle_scope.Escape(array);
  }
  if (PyObject_TypeCheck(value, &PyDomObject_Type)) {
    PyDomObject* proxy = reinterpret_cast<PyDomObject*>(value);
    PythonDomTarget* target = proxy->target_;
    if (target && target->isolate == isolate) {
      return handle_scope.Escape(target->target_handle.Get(isolate));
    }
  }
  PyErr_SetString(PyExc_TypeError, "unsupported python value");
  return handle_scope.Escape(v8::Undefined(isolate));
}

}  // namespace blink