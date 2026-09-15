// Copyright 2026 The Pymium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "content/renderer/pymium_embed.h"

#include <Python.h>

#include "base/check.h"
#include "third_party/blink/renderer/bindings/core/python/py_dom.h"
#include "third_party/blink/renderer/bindings/core/python/python_script_controller.h"
#include "third_party/blink/renderer/core/script/script_loader.h"
#include "third_party/blink/renderer/platform/bindings/script_state.h"
#include "third_party/blink/renderer/platform/wtf/text/wtf_string.h"

namespace blink {
namespace {

// Gate so the interpreter is brought up exactly once per renderer process,
// in lockstep with the CPython static archive built by
// //third_party/cpython/BUILD.gn (see third_party/cpython/README.md). Chromium's
// ThreadState must already be up; most callers route through
// PythonScriptController::InstallPythonForScriptType.
bool g_python_initialized = false;

void InstallWindowPython(ExecutionContext* execution_context) {
  auto* window_proxy = DOMWindow* /* see PythonScriptController */;
  (void)window_proxy;
  // Cookie-less, feature-flagged install: <script type="python"> is rejected
  // with a console error unless pymium_enable_python_runtime is set in
  // //build/config. The actual `window.python` binding goes to
  // python_js.cc via InstallPythonJS().
}

}  // namespace

void EnsurePythonRuntime(v8::Isolate* isolate) {
  if (g_python_initialized)
    return;
  CHECK(!PyGILState_Check()) << "Python runtime init on the wrong thread";
  Py_InitializeEx(0);  // 0 = don't install Python's signal handlers.
  g_python_initialized = true;
}

}  // namespace blink