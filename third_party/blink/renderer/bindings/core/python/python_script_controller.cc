// Copyright 2026 The Pymium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "third_party/blink/renderer/bindings/core/python/python_script_controller.h"

#include <Python.h>

#include "third_party/blink/public/mojom/devtools/console_message.mojom-blink.h"
#include "third_party/blink/renderer/bindings/core/python/py_dom.h"
#include "third_party/blink/renderer/core/execution_context/execution_context.h"
#include "third_party/blink/renderer/core/inspector/console_message.h"
#include "third_party/blink/renderer/platform/weborigin/kurl.h"
#include "third_party/blink/renderer/platform/wtf/hash_map.h"
#include "third_party/blink/renderer/platform/wtf/text/string_utf8.h"

extern "C" PyObject* PyInit__pymium_native(void);

namespace blink {
namespace {

constexpr char kPackagePath[] = "pymium-packages";
constexpr char kInterpreterGlobals[] =
    "import pymium, _pymium_native as __native\n"
    "pymium._install_native(__native)\n"
    "globals().update(pymium._page_globals())\n";

bool FormatPendingPythonError(String* message) {
  if (!PyErr_Occurred())
    return true;
  PyObject *etype = nullptr, *evalue = nullptr, *etb = nullptr;
  PyErr_Fetch(&etype, &evalue, &etb);
  PyErr_NormalizeException(&etype, &evalue, &etb);
  if (evalue) {
    PyObject* text = PyObject_Str(evalue);
    if (text) {
      const char* utf8 = PyUnicode_AsUTF8(text);
      *message = utf8 ? String::FromUTF8(utf8) : String("python error");
      Py_DECREF(text);
    }
  }
  Py_XDECREF(etype);
  Py_XDECREF(evalue);
  Py_XDECREF(etb);
  PyErr_Clear();
  return false;
}

void ReportConsoleError(ExecutionContext* context, const String& message) {
  context->AddConsoleMessage(MakeGarbageCollected<ConsoleMessage>(
      mojom::blink::ConsoleMessageSource::kJavaScript,
      mojom::blink::ConsoleMessageLevel::kError, message));
}

}  // namespace

PythonScriptController::PythonScriptController(ExecutionContext* context)
    : context_(context), globals_(nullptr) {}

PythonScriptController::~PythonScriptController() {}

PythonScriptController* PythonScriptController::From(
    ExecutionContext& context) {
  static WTF::HashMap<const void*, std::unique_ptr<PythonScriptController>>
      controllers;
  auto insert_result = controllers.insert(&context, nullptr);
  std::unique_ptr<PythonScriptController>& slot = insert_result->value;
  if (!slot)
    slot = std::make_unique<PythonScriptController>(&context);
  return slot.get();
}

void PythonScriptController::EnsureInterpreter() {
  if (globals_)
    return;
  PyImport_AppendInittab("_pymium_native", &PyInit__pymium_native);
  Py_InitializeEx(0);
  PyRun_SimpleString("import sys");
  PyRun_SimpleString("sys.path.insert(0, '" kPackagePath "')");
  PyRun_SimpleString(kInterpreterGlobals);
  PyObject* globals = PyModule_GetDict(PyImport_AddModule("pymium_page"));
  globals_ = globals ? Py_NewRef(globals) : nullptr;
}

bool PythonScriptController::ExecuteScriptSource(const String& source,
                                                 const KURL& source_url) {
  EnsureInterpreter();
  StringUTF8Adaptor source_utf8(source, kStrictUTF8Conversion);
  String filename = source_url.IsValid() ? source_url.GetString()
                                         : String("<pymium script>");
  StringUTF8Adaptor filename_utf8(filename);

  PyObject* compiled =
      Py_CompileString(source_utf8.data(), filename_utf8.data(), Py_file_input);
  if (!compiled) {
    String message;
    FormatPendingPythonError(&message);
    ReportConsoleError(context_,
                       "python compile error in " + filename + ": " + message);
    return false;
  }

  PyObject* result =
      PyEval_EvalCode(compiled, static_cast<PyObject*>(globals_),
                      static_cast<PyObject*>(globals_));
  Py_DECREF(compiled);
  if (!result) {
    String message;
    FormatPendingPythonError(&message);
    ReportConsoleError(context_,
                       "python error in " + filename + ": " + message);
    return false;
  }
  Py_DECREF(result);
  return true;
}

String PythonScriptController::Evaluate(const String& expression, bool* ok) {
  EnsureInterpreter();
  StringUTF8Adaptor expression_utf8(expression, kStrictUTF8Conversion);
  PyObject* result = PyRun_String(expression_utf8.data(), Py_eval_input,
                                  static_cast<PyObject*>(globals_),
                                  static_cast<PyObject*>(globals_));
  if (!result) {
    *ok = false;
    String message;
    FormatPendingPythonError(&message);
    ReportConsoleError(context_, "python eval error: " + message);
    return String();
  }
  *ok = true;
  PyObject* repr = PyObject_Repr(result);
  Py_DECREF(result);
  if (!repr) {
    PyErr_Clear();
    return String("<unrepresentable>");
  }
  const char* utf8 = PyUnicode_AsUTF8(repr);
  String text = utf8 ? String::FromUTF8(utf8) : String("<unrepresentable>");
  Py_DECREF(repr);
  return text;
}

}  // namespace blink