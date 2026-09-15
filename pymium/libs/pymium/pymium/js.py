"""Call JavaScript from Python (the mirror of window.python, useful the other
way round). Only meaningful inside a Pymium renderer; outside one, access
raises PyumiumNotEmbedded.
"""
from . import _bridge
from ._bridge import native


def eval(expression):
    return native().eval(expression)


def run(code, filename="<js>"):
    return native().run(code, filename)


def function(code):
    return native().js_function(code)


def get_global(name):
    return native().get_global(name)


def __getattr__(name):
    if name in ("window", "document", "console", "navigator", "location",
                "history", "alert"):
        return get_global(name)
    raise AttributeError(name)


__all__ = ["eval", "run", "function", "get_global"]