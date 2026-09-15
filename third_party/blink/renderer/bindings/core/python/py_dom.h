// Copyright 2026 The Pymium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#ifndef THIRD_PARTY_BLINK_RENDERER_BINDINGS_CORE_PYTHON_PY_DOM_H_
#define THIRD_PARTY_BLINK_RENDERER_BINDINGS_CORE_PYTHON_PY_DOM_H_

#include <Python.h>

#include "third_party/blink/renderer/platform/wtf/text/wtf_string.h"
#include "v8/include/v8.h"

namespace blink {

// A PythonDomTarget owns the v8 handles that keep a Blink object alive on the
// JavaScript heap while Python holds a reference to it. No second copy of the
// DOM exists; any mutation performed through this proxy is a real Blink
// operation (ARCHITECTURE.md section 3.3).
struct PythonDomTarget {
  v8::Global<v8::Object> target_handle;
  v8::Global<v8::Context> context_handle;
  v8::Isolate* isolate = nullptr;
};

struct PyDomObject {
  PyObject_HEAD
  PythonDomTarget* target_;
};

struct PyDomMethod {
  PyObject_HEAD
  PyObject* self_;
  PyObject* name_;
};

// Python <-> v8 marshalling. The isolate-side entry points reach here; the
// actual bridge module (_pymium_native) delegates to these.
PyObject* PyObject_FromV8(v8::Isolate* isolate,
                          const v8::Local<v8::Value>& value,
                          const v8::Local<v8::Context>& context);

v8::Local<v8::Value> PyObject_ToV8(v8::Isolate* isolate,
                                   const v8::Local<v8::Context>& context,
                                   PyObject* value);

extern PyTypeObject PyDomObject_Type;
extern PyTypeObject PyDomMethod_Type;

}  // namespace blink

#endif  // THIRD_PARTY_BLINK_RENDERER_BINDINGS_CORE_PYTHON_PY_DOM_H_