# Pymium CPython third-party side.
# =================================
#
# Pymium embeds CPython (>= 3.11) in the Blink renderer *without* importing it
# into the same binary that links V8 from `v8_use_external_startup_data` in the
# upstream build. Rationale (ARCHITECTURE.md section 4.1):
#
#   1. CPython and V8 both install signal handlers and both might register
#      their own allocators; keeping them in the same ELF/PE image is legal but
#      couples GC (V8) with refcounting (CPython) in ways the browser can't
#      audit. We therefore build CPython as a *separate* static archive with
#      its own config (PYM $PYMIUM_CPYTHON_CONFIG) and rely on the tools/
#      bridge to translate the two object models.
#   2. The interpreter is created once per renderer process, never per
#      frame/origin. Python programs are isolated by origin at the Blink layer
#      (python_script_controller) rather than by a CPython mechanism, because a
#      single process-global interpreter is what keeps `window` / `document`
#      identity meaningful (ARCHITECTURE.md section 3.1).
#   3. GC strategy is *conservative stay-in-place*: Blink DOM objects live in
#      V8; Python never owns a second copy code. PyDomObject proxies carry a
#      v8::Global pin that keeps the live Blink object reachable while Python
#      holds the reference (see py_dom.h in this directory).

## Build integration
#
# BUILD.gn here never touches the top-level `//build` helper templates: it
# reuses `source_set("cpython")` from //third_party/cpython/BUILD.gn (upstream)
# and only adds the exported include dir (third_party/cpython) plus the `-lpym`-
# style link flags expected by the Python extension ABI (stable for >=3.11).
#
# The `tools/` bridge (pymium_embed.{cc,h}) finds the interpreter by calling
# Py_InitializeEx from this build target's `dynamic_deps`? - no. The interpreter
# is created lazily the first time a script_type=="python" <script> is seen,
# from content/renderer/pymium_embed.cc, which compiles this same header via
# the include chain:
#
#   content/renderer/pymium_embed.cc
#       -> third_party/blink/renderer/bindings/core/python/python_script_controller.h
#       -> .../py_dom.h (PythonDomObject, PythonDomMethod)
#       -> <Python.h>  (this package)

## Files in this directory
#   README.md       this file
#   BUILD.gn        the GN target that links CPython
#   build.py        invoked by //third_party/cpython/BUILD.gn? not directly -
#                   kept as a reference for `gclient runhooks` parity; a real
#                   fork would vendor a CPython tarball under //third_party/
#                   and let //build/checkouts breathe. See conf/gn_args.txt
#                   (pymium_cpython_version / pymium_cpython_hash).
