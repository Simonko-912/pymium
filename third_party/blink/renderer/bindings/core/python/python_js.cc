// Copyright 2026 The Pymium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "third_party/blink/renderer/bindings/core/python/python_js.h"

#include "third_party/blink/renderer/bindings/core/python/python_script_controller.h"
#include "third_party/blink/renderer/bindings/core/v8/script_state.h"
#include "third_party/blink/renderer/core/execution_context/execution_context.h"
#include "third_party/blink/renderer/platform/weborigin/kurl.h"
#include "third_party/blink/renderer/platform/wtf/text/wtf_string.h"

namespace blink {
namespace {

String ToWtfString(v8::Isolate* isolate, v8::Local<v8::Value> value) {
  v8::String::Utf8Value utf8(isolate, value.As<v8::String>());
  return String::FromUTF8(*utf8, static_cast<unsigned>(utf8.length()));
}

PythonScriptController* CurrentController(v8::Isolate* isolate) {
  ScriptState* script_state = ScriptState::Current(isolate);
  if (!script_state)
    return nullptr;
  return PythonScriptController::From(*ExecutionContext::From(script_state));
}

void PythonRun(const v8::FunctionCallbackInfo<v8::Value>& info) {
  v8::Isolate* isolate = info.GetIsolate();
  v8::HandleScope handle_scope(isolate);
  if (info.Length() < 1 || !info[0]->IsString()) {
    isolate->ThrowException(v8::Exception::TypeError(
        v8::String::NewFromUtf8Literal(isolate, "python.run(code[, name])")));
    return;
  }
  String source = ToWtfString(isolate, info[0]);
  PythonScriptController* controller = CurrentController(isolate);
  if (!controller)
    return;
  controller->ExecuteScriptSource(source, KURL());
}

void PythonEval(const v8::FunctionCallbackInfo<v8::Value>& info) {
  v8::Isolate* isolate = info.GetIsolate();
  v8::HandleScope handle_scope(isolate);
  if (info.Length() < 1 || !info[0]->IsString()) {
    isolate->ThrowException(v8::Exception::TypeError(
        v8::String::NewFromUtf8Literal(isolate, "python.eval(expression)")));
    return;
  }
  String expression = ToWtfString(isolate, info[0]);
  PythonScriptController* controller = CurrentController(isolate);
  if (!controller)
    return;
  bool ok = false;
  String result = controller->Evaluate(expression, &ok);
  if (ok)
    info.GetReturnValue().Set(v8::String::NewFromUtf8(isolate, result.Utf8().c_str())
                                 .ToLocalChecked());
}

void PythonVersion(const v8::FunctionCallbackInfo<v8::Value>& info) {
  v8::Isolate* isolate = info.GetIsolate();
  v8::Local<v8::Context> context = isolate->GetCurrentContext();
  v8::Local<v8::Array> version = v8::Array::New(isolate, 5);
  version->Set(context, 0, v8::Number::New(isolate, 3)).Check();
  version->Set(context, 1, v8::Number::New(isolate, 13)).Check();
  version->Set(context, 2, v8::Number::New(isolate, 0)).Check();
  version->Set(context, 3,
               v8::String::NewFromUtf8Literal(isolate, "pymium"))
      .Check();
  version->Set(context, 4, v8::Number::New(isolate, 0)).Check();
  info.GetReturnValue().Set(version);
}

}  // namespace

void InstallPythonJS(v8::Isolate* isolate, v8::Local<v8::Object> global) {
  v8::Local<v8::Context> context = isolate->GetCurrentContext();
  v8::Local<v8::Object> python = v8::Object::New(isolate);
  python
      ->Set(context,
            v8::String::NewFromUtf8Literal(isolate, "run"),
            v8::Function::New(context, PythonRun, v8::Integer::New(isolate, 0))
                .ToLocalChecked())
      .Check();
  python
      ->Set(context, v8::String::NewFromUtf8Literal(isolate, "eval"),
            v8::Function::New(context, PythonEval, v8::Integer::New(isolate, 0))
                .ToLocalChecked())
      .Check();
  python
      ->Set(
          context, v8::String::NewFromUtf8Literal(isolate, "version"),
          v8::Function::New(context, PythonVersion,
                            v8::Integer::New(isolate, 0))
              .ToLocalChecked())
      .Check();
  global->Set(context, v8::String::NewFromUtf8Literal(isolate, "python"),
              python)
      .Check();
}

}  // namespace blink