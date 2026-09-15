# Pymium roadmap

Milestones are ordered so each one is shippable and testable on its own. The first
working milestone is "content_shell can run `<script type="text/python">` with the
pymium package".

## M0 — Scaffold (this repo)

- [x] Fork layout, bootstrap scripts, GN args
- [x] Patch queue with NEW / REBASE annotations
- [x] `pymium` Python package (dual API) with standalone pytest suite
- [x] Architecture + security + testing docs

## M1 — Interpreter boots in the renderer

- [ ] Pin your own chromium/src fork + push upstream (set `PYMIUM_FORK_URL`)
- [ ] Rebase `0001` edits (`git apply --3way`), confirm `kPython` compiles
- [ ] Add `use_pymium` arg, build `third_party/cpython` gate
- [ ] `Py_Initialize` runs at first use; unit test marshalling table
- [ ] `python_shell` (content shell variant) `print("hi")` reaches console
- **Exit criteria:** `./content_shell --pymium-fixture=/hy hello.html` prints `hello`.

## M2 — `<script type="text/python">` end-to-end

- [ ] `ScriptLoader` routes to `PythonScriptController`
- [ ] Parser-blocking semantics verified against `html5lib`-style fixture suite
- [ ] DOM bridge: `PyDomProxy` attribute + call path green
- [ ] `pymium` injected globals (`window`, `document`, `console`)
- [ ] web_tests harness green for `web_tests/python/*.html`
- **Exit criteria:** the README demo page works in `out/pymium/chrome`.

## M3 — Full event + async surface

- [ ] `addEventListener`/`on_<event>` dispatch into Python callables
- [ ] `setTimeout`/`setInterval`/`requestAnimationFrame` non-blocking tasks
- [ ] `fetch` + `pymium.html` + `console` polish
- [ ] audit-hook security policy + policy tests
- [ ] fuzz corpus for `py_dom.cc`
- **Exit criteria:** interactive click/drag/keystroke demo app in pure Python.

## M4 — Platform hardening

- [ ] dedicated python renderer process option (jank isolation)
- [ ] OOMInterruption / watchdog integration for long Python tasks
- [ ] JIT/GC interop review: V8 object lifetime under `v8::Global` trace
- [ ] telemetry (memory, per-script CPU) 
- [ ] update all patches to a fresh chromium tip-of-tree and re-run web_tests

## M5 — Ecosystem

- [ ] pip-installable CPython packages usable from `<script type="text/python">`
- [ ] devtools panel for python sources / audit events
- [ ] spec-style draft for `<script type="text/python">` document
- [ ] CI: nightly patch-rebase + compile + web_tests