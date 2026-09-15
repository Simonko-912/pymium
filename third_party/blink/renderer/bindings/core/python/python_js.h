// Copyright 2026 The Pymium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#ifndef THIRD_PARTY_BLINK_RENDERER_BINDINGS_CORE_PYTHON_PYTHON_JS_H_
#define THIRD_PARTY_BLINK_RENDERER_BINDINGS_CORE_PYTHON_PYTHON_JS_H_

#include "v8/include/v8.h"

namespace blink {

void InstallPythonJS(v8::Isolate* isolate, v8::Local<v8::Object> global);

}  // namespace blink

#endif  // THIRD_PARTY_BLINK_RENDERER_BINDINGS_CORE_PYTHON_PYTHON_JS_H_