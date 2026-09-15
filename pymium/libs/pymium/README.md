# pymium

The Python package that ships inside Pymium (a Chromium fork) to give Python the
full web platform: DOM, events, timers, console, and JavaScript interop.

This repository-level copy is a normal pip package so the API can be developed and
tested outside the browser against a local mirror. When running inside a Pymium
renderer, the native `_pymium_native` extension is wired in with
`pymium.install_native(...)` and the same objects operate on the live DOM.

```python
# Pymium browser-style
from pymium import document, console

btn = document.getElementById("go")
btn.addEventListener("click", lambda e: console.log("hi"))

# Pymium pythonic
@btn.on_click
def clicked(event):
    with document.querySelector("#out"):
        ...  # bulk edits

print("lands in the page console")
```

Run the standalone tests:

```sh
pip install -e .
python -m pytest
```