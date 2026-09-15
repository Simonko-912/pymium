# Pymium architecture

This document explains how a stock Chromium tree is turned into Pymium. It maps each
conceptual change onto real `blink/` and `content/` files, and marks every hunk that
touches existing upstream code as **REBASE** (context-sensitive) versus brand-new files
which apply cleanly.

## 1. What changes, at a glance

Chromium's script model has exactly two product-facing script kinds: classic and
module, both JavaScript, both compiled and executed by V8. Pymium adds a third kind,
`python`, executed by an embedded CPython, and grows four components:

| # | Component | Where | Kind |
|---|-----------|-------|------|
| 1 | `<script type="text/python">` is a recognised script kind | `blink/renderer/core/script/` | REBASE |
| 2 | Python runtime: interpreter embedding, V8<->Python marshalling, DOM bridge | `blink/renderer/bindings/core/python/` | NEW |
| 3 | CPython third-party dep + GN wiring + `use_pymium` flag | `third_party/cpython/`, `build/config/pymium.gni` | NEW |
| 4 | Renderer init + `window.python` JS API | `content/renderer/`, `blink/public/web/` | NEW + one REBASE hook |

## 2. Blink script pipeline today

```
HTMLScriptElement
  └─ ScriptLoader (core/script/script_loader.cc)
       └─ GetScriptType() → ScriptType::kClassic | kModule   ← (1)
            └─ ClassicScript / ModuleScript
                 └─ ScriptRunner (core/script/script_runner.cc)
                      └─ ScriptController (bindings/core/v8/script_controller.cc)
                           └─ V8ScriptRunner::CompileAndRunScript
```

The attributes that matter are the `type`/`language` attribute on the `<script>`
element and `ScriptLoader::IsValidScriptTypeAndLanguage()`, which today only accepts
empty / `text/javascript` / `module` / `importmap` / `speculationrules`.

### Change (1): `ScriptType::kPython`

* In `script_loader.cc` add a `kPython` value beside `kModule` and return it when the
  `type` attribute (or legacy `language`) is one of
  `text/python`, `python`, `application/x-python`, `text/x-python`.
* The parser and script scheduling treat a python script exactly like a classic
  script: it is fetched, decoded, and executed synchronously in document order. That
  matches `<script type="text/python">` semantics a web developer expects, and — a
  deliberate decision — initial implementation is **parser-blocking**, i.e. the
  blocker API (`PendingScript::BlockParser`) is reused unchanged so pages can rely on
  order and mutation of the (unparsed) subsequent DOM.
* `ScriptLoader::ExecuteScriptBlock` routes to a new
  `PythonScriptController::ExecuteScriptSource()`, not to V8.

These wirings are the REBASE hunks in `0001-...patch`.

## 3. Change (2): the Python runtime

All new code lives in `third_party/blink/renderer/bindings/core/python/`
(`0002-...patch`, all NEW files). This is deliberately a *thin native core*: it
marshals values, runs bytecode, and exposes a bridge object `_pymium_native`. Every
"JavaScript feature for Python" — DOM methods, events, timers, console, fetch — is
implemented in **Python** in the `pymium` package (`libs/pymium/`). Consequence:
behaviour is trivially iterable, testable, and patch-friendly; the C++ stays small
and auditable.

### 3.1 Interpreter lifecycle

* One interpreter per renderer process, created lazily on the main thread the first
  time a python script (or `window.python`) is used:
  `PyImport_AppendInittab("_pymium_native", ...)`, then `Py_InitializeEx(0)`.
* The `pymium` package (shipped as part of the image via `//libs/pymium`) is put on
  `sys.path`; after initialization the bridge injects the platform globals
  (`window`, `document`, `console`, `navigator`, ...) directly into both the builtins
  namespace and the module-level namespace of every python script, exactly as V8's
  `window` is the implicit global for scripts.
* Isolation: each DOMWindow gets its own module namespace dict (`PyModule_New` +
  per-frame globals), so two tabs don't share state; only interned type objects and
  the interpreter are shared.

### 3.2 GIL and the Blink event loop

CPython needs the GIL; Blink's main thread is a Chromium `MessageLoop`. Rules:

* Python code runs to completion (or until it yields) as one Blink task posted to the
  main thread task runner, exactly like a JS macro-task. Parser-blocking semantics
  (section 2) makes ordering deterministic.
* **M1 bridge rule: do not call into V8 while holding the GIL if the call could
  block or re-enter Python.** Attribute/property access on DOM proxies is a short,
  synchronous V8 round trip and holds the GIL. Anything that can *block* (fetch,
  timers, IPC) is implemented via non-blocking task posting, and any future path
  that could re-enter Python (e.g. arbitrary JS getters) must first release the GIL
  with `Py_BEGIN_ALLOW_THREADS`. This avoids the classic GIL + V8 isolate deadlock:
  JS calling `python.eval()` (which takes the GIL) while Python calls `js.foo()`
  (which must re-enter V8) can both proceed because at most one of the two locks is
  held while a cross-language call is in flight.
* `setTimeout`/`setInterval`/`fetch` in `pymium` are *non-blocking*: they record a
  Blink timer / start a fetch and post a Python callable to the task runner later.
  A Python `while True:` loop is a blocking loop and — same as a JS busy-loop —
  starves the main thread; that is documented, not supported.
* A `sys.audit` hook additionally fires on blocking calls (`time.sleep`, `socket`
  connect, long-running `datetime`/decimal) so the host can warn in the console.

### 3.3 Marshalling table (`py_dom.cc`)

`PyObject*` <-> `v8::Local<v8::Value>` conversion, mirroring V8's own data model:

| Python | V8 |
|--------|----|
| `None` | `undefined` (also accepts `null` on the Python side as `None` aliasing `v8::Null`) |
| `int` | `Number` (lossy beyond 2^53, documented) |
| `float` | `Number` |
| `bool` | `Boolean` |
| `str` | `String` (UTF-16 aware) |
| `bytes` | `Uint8Array` |
| `list`/`tuple` | `Array` |
| `dict` | `Object` with `String` keys |
| `PyDomProxy` | the wrapped DOM object (see below) |
| any other `Callable` | `v8::Function` wrapper |
| `pymium.Exception` subclasses | thrown JS `DOMException` / `TypeError` |

On the V8 side the same table applies in reverse; `Symbol`/`BigInt`/`RegExp`/typed
arrays map to dedicated Python proxy types in `pymium/js.py` rather than being
flattened.

### 3.4 The DOM bridge

No copy of the DOM is ever maintained in Python. A `PyDomProxy` is a Python instance
whose single payload is a `v8::Global<v8::Object>` (kept alive by the blink heap
handle wrapper). Getting an attribute does:

1. enter the owning `v8::Context` (`v8::Context::Scope`),
2. `object->Get(context, name)`,
3. convert the result with the table above — a `v8::Function` becomes a bound
   `PyDomCallback` that invokes `v8::Function::Call` lazily.

So `document.querySelector(...)` in Python is, under the hood, a real
`Document::querySelector` call. The element handle stays live for as long as the
Python proxy is referenced; Blink's `v8::Global` tracing keeps the underlying DOM
node alive appropriately.

Exceptions crossing the boundary become `pymium.Exception` subclasses carrying the
DOMException name/message, so `except pymium.DOMException:` is meaningful.

### 3.5 `_pymium_native` extension module

Small `PyMethodDef[]` table exposed to Python:

* `run(source, filename)` – compile+exec in the frame's namespace
* `eval(expr)` – eval in the frame's namespace
* `get_native(name)` – return the `PyDomProxy` for a named platform object
  (e.g. `document`)
* `js_call(proxy, js_name, args)` – attribute fetch + call in one V8 round trip
* `install_module(name, module)` – used to install the `pymium` package globals
* `audit(name, event, args)` – module-level `sys.audit` helper
* `version()` – CPython/Pymium version tuple

## 4. Change (3): CPython as third_party

* DEPS entry pinned to a CPython release commit (`pymium_cpython_version` +
  `pymium_cpython_hash` in `conf/gn_args.txt`) so builds are reproducible.
* `third_party/cpython/BUILD.gn` builds a static `libpython3.x` and exposes headers;
  `third_party/cpython/README.md` documents the build flags used
  (`Py_ENABLE_SHARED=0`, `Py_DEBUG` off by default, `use_pymium` gate).
* `build/config/pymium.gni` declares `use_pymium` (default `false`), wiring the flag
  through to `blink`, `content`, and cpython targets.

## 5. Change (4): renderer init and the JS side

* `content/renderer/pymium_embed.{h,cc}` (NEW) primes the interpreter lazily and,
  critically, registers a **pre-`chrome` `v8::Extension`** named `python`
  (`python_js.cc`) that materialises `window.python` for every main world context.
  `window.python` exposes exactly what `pymium` needs and nothing more:

  ```js
  window.python.run(code, filename);
  window.python.eval(expression);          // -> value marshalled per table
  window.python.version;                    // [3, 13, x, pymium, 0]
  window.python.audit_events;               // last N audit events (console tooling)
  ```

* The only REBASE hook in this area is one `#include` + one initializer call added to
  the renderer platform init path (kept as a two-line diff; the surrounding context
  moves between Chromium revisions).

## 6. The `pymium` package

The full browser API for Python. Two styles, same objects:

* **browser-style** — mirrors JavaScript mechanics and naming so existing web devs
  and existing JS code can be ported line-for-line: `document.getElementById`,
  `element.innerHTML = ...`, `addEventListener`, `console.log`, `fetch(...).then`.
* **pythonic** — idiomatic leanings so Python authors get what they'd expect:
  snake_case aliases (`get_element_by_id`, `query_selector`), `with element:` bulk
  editing, `element.on("click")` and `@element.on_click` decorators, `.text = ...`,
  `.classes.add("show")`, and `print()` that lands in the page console.

Both are provided by the same `Element`/`Document`/`Window` classes in
`libs/pymium` (`browser.py`, `events.py`, `js.py`, `html.py`). The package also ships
`pymium.html` (JSX-style helpers to *author* markup from Python) and `pymium.js` for
the reverse interop. See `libs/pymium/tests/` for behavioural examples, runnable
outside the browser through a local mirror.

## 7. Security model

* Python in the renderer is third-party code executing under the same sandbox as JS.
  The new attack surface is (a) the CPython interpreter itself in the renderer
  process, (b) the marshalling layer, (c) the audit/security policy. These receive
  the same attention as V8: fuzzing for `py_dom.cc`, a corpus of boundary tests for
  the marshalling table, and a **static `sys.audit` hook policy** that denies, for
  web-authored pages: `import` of anything outside an allowlist of pure-Python stdlib
  modules, `ctypes`, `subprocess`, `socket`, `resource`, `os.system`, and file-system
  writes. `help()`/`type()` interactive recon is limited by listing only the injected
  platform objects.
* Resource limits: the same source-text and execution limits that apply to JS
  (script source size cap, suspensable/alarming long tasks) are applied to python
  sources; a runaway Python task is killable through the same renderer
  crash/kill machinery (`OOMIntervention`, watchdog).
* No new IPC surfaces are added in M1; everything stays in-process. Later milestones
  (dedicated python renderer, jank-scheduler integration) are tracked in ROADMAP.

## 8. Testing plan

| Layer | Where | What |
|-------|-------|------|
| marshalling unit tests | `blink/renderer/bindings/core/python/*_unittest.cc` | each row of the table plus proxies |
| embed smoke test | `content/test/pymium_shell` | `content_shell` that loads a fixture and asserts on console output |
| web tests | `web_tests/python/` | `python-*.html` fixtures run by the existing `web_tests` harness (they don't care the script isn't JS) |
| interop | `web_tests/python/interop/*` | JS `<->` Python round trips |
| package | `libs/pymium/tests/` | pytest for the `pymium` API (runs standalone) |

## 9. Rebase workflow

Every Chromium revision moves context. The discipline is:

1. `patches/SERIES` annotates each patch `NEW` (deterministic) or `REBASE`.
2. After `gclient sync` to a new revision, run `tools/rebase_patches.py --src src`.
3. `NEW` patches apply silently; `REBASE` patches first try `git apply --3way` and,
   if that fails, leave a `*.rej` and a row in the failure report for a human.
4. Rebase small and often — the entire C++ delta is intentionally under ~1.5k LOC.

**Do not hand-edit the `NEW` patch files.** Under the single-repo model the
`chromium/src`-path files at the repo root ARE the source of truth and are
committed directly to the fork (that is what makes this a real browser fork
rather than an overlay patch set). `pymium/patches/0002`–`0004` are generated
from those tree files purely as reference documentation: run
`python pymium/tools/gen_new_file_patches.py` after touching anything under the
root paths; it re-diffs each file against `/dev/null` with `git diff`, so hunk
counts and content escaping are always exact (`git apply --check` on the three
patches passes in a fresh scratch clone). `0001` and `0005` stay as REBASE
reference hunks because they touch existing upstream `script_type.h` /
`script_loader.cc` / `script_extensions.cc` whose context cannot be reproduced
outside a real `chromium/src` checkout.

## 10. File map (new paths)

```
build/config/pymium.gni
third_party/cpython/{README.md, BUILD.gn, build.py}
third_party/blink/renderer/bindings/core/python/
  BUILD.gn
  python_script_controller.{h,cc}
  py_dom.{h,cc}
  python_js.{h,cc}
content/renderer/pymium_embed.{h,cc}
```

Each path above lives once, at its `chromium/src` location at the repo root, and is
committed directly to the fork. `pymium/patches/0002/0003/0004-*.patch` are generated
from those files as reference copies via `tools/gen_new_file_patches.py`.