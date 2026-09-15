// Copyright 2026 The Pymium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#ifndef CONTENT_RENDERER_PYMIUM_EMBED_H_
#define CONTENT_RENDERER_PYMIUM_EMBED_H_

#include "v8/include/v8.h"

namespace blink {

// Lazy-init function called from the renderer main thread. If the current
// renderer process has not yet initialized a Python sub-interpreter (M1:
// one per renderer process, no per-frame isolation), this creates it, runs
// the pymium bootstrap module, and then installs `window.python` on the
// global object of every origin that has opted in via <script type="python">.
//
// Safe to call multiple times; a `static bool` gate prevents redundant work.

void EnsurePythonRuntime(v8::Isolate* isolate);

}  // namespace blink

#endif  // CONTENT_RENDERER_PYMIUM_EMBED_H_
