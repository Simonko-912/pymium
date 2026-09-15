// Copyright 2026 The Pymium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#ifndef THIRD_PARTY_BLINK_RENDERER_BINDINGS_CORE_PYTHON_PYTHON_SCRIPT_CONTROLLER_H_
#define THIRD_PARTY_BLINK_RENDERER_BINDINGS_CORE_PYTHON_PYTHON_SCRIPT_CONTROLLER_H_

#include "third_party/blink/renderer/core/core_export.h"
#include "third_party/blink/renderer/platform/wtf/text/wtf_string.h"

namespace blink {

class ExecutionContext;
class KURL;

class CORE_EXPORT PythonScriptController {
 public:
  explicit PythonScriptController(ExecutionContext* context);
  ~PythonScriptController();

  static PythonScriptController* From(ExecutionContext& context);

  bool ExecuteScriptSource(const String& source, const KURL& source_url);

  String Evaluate(const String& expression, bool* ok);

 private:
  void EnsureInterpreter();

  ExecutionContext* context_;
  void* globals_;
};

}  // namespace blink

#endif  // THIRD_PARTY_BLINK_RENDERER_BINDINGS_CORE_PYTHON_PYTHON_SCRIPT_CONTROLLER_H_