"""Pymium: the web platform for Python.

Running inside a Pymium renderer, the embedded interpreter imports this package
and the bridge (calling pymium._install_native(_pymium_native)) swaps every
mirror object onto the live DOM. Outside a renderer everything is a faithful
local mirror, which is how the standalone test suite works.
"""
import builtins as _builtins

from . import _bridge, browser, events, html, js
from ._bridge import enabled, install_native, native, PyumiumNotEmbedded
from .browser import (window, document, console, navigator, location, history)
from .events import Event, EventTarget
from .html import escape, h, markup

__version__ = "0.1.0"

__all__ = [
    "window", "document", "console", "navigator", "location", "history",
    "Event", "EventTarget",
    "h", "markup", "escape",
    "js",
    "install_native", "enabled", "native", "PyumiumNotEmbedded",
    "install_print", "page_globals", "__version__",
]


def _print_to_pymium(*args, sep=" ", end="\n", file=None, flush=False):
    del file, flush
    text = sep.join(str(arg) for arg in args)
    console.log(text.rstrip("\n") if end == "\n" else text + end)


def install_print():
    """Route builtin print() into the page console once a bridge is present."""
    if enabled():
        _builtins.print = _print_to_pymium
    return enabled()


def page_globals():
    """Globals injected into every <script type="text/python"> block."""
    return {
        "window": window,
        "document": document,
        "console": console,
        "navigator": navigator,
        "location": location,
        "history": history,
        "Event": Event,
        "EventTarget": EventTarget,
        "alert": window.alert,
        "python": js,
    }


def _install_native(native_module):
    install_native(native_module)
    install_print()


def _page_globals():
    return page_globals()