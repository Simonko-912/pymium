# Pymium

A Chromium fork whose entire purpose is to support **Python in the browser**.

Where Chromium only understands `<script>` as JavaScript, Pymium adds a first-class
**`<script type="text/python">`** script kind back by an embedded CPython interpreter
in the renderer process, plus a Python standard-library package called **`pymium`**
that reproduces every "JavaScript feature" of the web platform for Python: the DOM,
events, timers, `console`, `fetch`, and more.

```html
<!doctype html>
<html>
<head>
  <script type="text/python">
from pymium import document, console

button = document.getElementById("go")

@button.on_click
def clicked(event):
    document.querySelector("#out").text = f"Clicked {event.clientX},{event.clientY}"
    console.log("handled in Python!")
  </script>
</head>
<body>
  <button id="go">press me</button>
  <p  id="out"></p>
</body>
</html>
```

## Status

This repository is a **single-repo Chromium fork scaffold**: the Chromium-path
files live directly in the tree at their `chromium/src` locations (so they could
be merged into a real `chromium/src` checkout as plain new files), joined by build
wiring, patch-reference documentation, design docs, and the `pymium` Python library.

The patch queue and architecture are written against a recent `chromium/src`. Building
an actual browser requires the usual Chromium rig: depot_tools, ~30 GB checkout,
tens of GB of toolchain, and a build measured in hours. This scaffold intentionally
keeps every patch as small and readable as it can, and the `patches/SERIES` file flags
which hunks are `NEW` (deterministic to apply) versus `REBASE` (context depends on the
exact upstream revision and may need `git apply --3way` or a human).

## Repository layout

```
pymium/
  bootstrap.ps1 / bootstrap.sh   one-shot dev machine setup (depot_tools + fetch)
  conf/gn_args.txt               build args enabling use_pymium
  tools/rebase_patches.py        applies the patch queue, tolerates context drift
  tools/gen_new_file_patches.py  regenerates 0002-0004 reference patches from the tree
  patches/
    SERIES                       ordered queue + apply-mode annotations
    0001-...patch                REBASE reference: teach the HTML parser a third script type
    0002-...patch                NEW reference: the Blink Python runtime (embedding + DOM bridge)
    0003-...patch                NEW reference: third_party/cpython + GN wiring + build/config/pymium.gni
    0004-...patch                NEW reference: content/renderer embedding init + window.python JS API
    0005-...patch                REBASE reference: one-line window.python install hook
  libs/pymium/                   source for the pip-installable `pymium` Python package
    pymium/
      browser.py                 window / document / elements / console ... dual API
      events.py                  Event + EventTarget with decorator/`on()` handlers
      js.py                      call JS from Python
      html.py                    tags / helpers so Python can author markup
      _bridge.py                 talk to the native _pymium_native extension
    tests/                       pytest suite (runs outside the browser via a local harness)
  docs/ROADMAP.md
  ARCHITECTURE.md                how the fork actually works under the hood

# The Chromium-source files themselves (at their chromium/src locations):
build/config/pymium.gni                                   build wiring (use_pymium flag)
content/renderer/pymium_embed.h / .cc                     renderer embedding init
third_party/cpython/BUILD.gn build.py README.md           CPython vendoring
third_party/blink/renderer/bindings/core/python/          the Blink Python runtime
    BUILD.gn py_dom.* python_js.* python_script_controller.*

The patches under pymium/patches are generated from these tree files as reference
documentation (they do not need applying — the files already exist).
```

## Quick start (library)

The `pymium` Python package in `libs/pymium` is what gets deployed into the embedded
interpreter as `pymium`. It is a normal pip package so its API can be exercised and
tested outside Chromium (against a local mirror) first.

```
pip install -e pymium/libs/pymium
python -m pytest pymium/libs/pymium/tests
```

## Quick start (browser)

1. The default fork URL is already your `chromium/src` fork
   (`https://github.com/Simonko-912/pymium`).
   To use your own, set `PYMIUM_FORK_URL` before running bootstrap.
2. Windows:

   ```
   .\pymium\bootstrap.ps1      # depot_tools + fetch
   cd src
   gn gen out/pymium
   autoninja -C out/pymium chrome
   ```

   Linux/macOS: `bash pymium/bootstrap.sh` then the same `gn` / `autoninja` steps.

3. Write a `demo.html` using `<script type="text/python">` as above and open it
   with `out/pymium/chrome demo.html`.

## Design notes

* The formal architecture, GIL / event-loop strategy, V8<->Python marshalling table,
  DOM bridge design, security model and test plan live in **`ARCHITECTURE.md`**.
* **`docs/ROADMAP.md`** sequences the work: make the patches compile, get the DOM
  bridge correct, then widen coverage of web platform surface.

## FAQ

**Why not Pyodide / PyScript?** Both are excellent and work today in stock browsers
by shipping CPython to WebAssembly plus a JS shim. Pymium is the "real fork" endgame:
`<script type="text/python">` is a native script kind with no shim, `import` goes
through Blink's resource loading, `window.python` is a true native JS API, and the
`pymium` package is the platform's own DOM binding. The two approaches are compatible —
`pymium`'s API is deliberately aligned so code written against Pyodide's `js` module
transfers with almost no friction.

**Is this secure?** No more or less than JavaScript: same-origin scripts are third-party
code executing in a sandboxed renderer. Embedding CPython adds attack surface (see the
ARCHITECTURE security section) which is why the scaffold pins the exact CPython version,
keeps ctypes/_socket-style capabilities out of reach for web-authored pages, and
directs review at the marshalling layer.

**License:** the fork inherits Chromium's BSD/BSD+patent; `libs/pymium` is BSD-3-Clause.