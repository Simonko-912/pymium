"""Browser objects with dual API: browser-style (getElementById, innerHTML,
addEventListener) and pythonic (get_element_by_id, text, on/on_click).

Outside a Pymium renderer every object is a faithful local mirror; inside one
the same methods route through the native _pymium_native bridge to the live DOM.
"""
from __future__ import annotations

import html as _stdlib_html
import threading

from . import _bridge
from .events import Event, EventTarget

_EMPTY = object()


def _escape(text):
    return _stdlib_html.escape(str(text), quote=False)


def _camel(name):
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


class _Style:
    def __init__(self, element):
        object.__setattr__(self, "_element", element)
        object.__setattr__(self, "_props", {})

    def set_property(self, name, value, _priority=""):
        self._props[name] = str(value)

    def setProperty(self, name, value, priority=""):
        self.set_property(name, value, priority)

    def get_property_value(self, name):
        return self._props.get(name, "")

    def getPropertyValue(self, name):
        return self.get_property_value(name)

    def remove_property(self, name):
        self._props.pop(name, None)

    def removeProperty(self, name):
        self.remove_property(name)

    def css_text(self, separator="; "):
        return "; ".join(f"{k}: {v}" for k, v in self._props.items())

    @property
    def cssText(self):
        return self.css_text()

    def __getattr__(self, name):
        css = name.replace("_", "-")
        if css in self._props:
            return self._props[css]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        if name.startswith("_"):
            object.__setattr__(self, name, value)
        else:
            self._props[name.replace("_", "-")] = str(value)


class _ClassList:
    def __init__(self, element):
        object.__setattr__(self, "_element", element)

    def _current(self):
        raw = self._element.get_attribute("class")
        return set(raw.split()) if raw else set()

    def _commit(self, classes):
        self._element.set_attribute("class", " ".join(sorted(classes)))

    def add(self, *names):
        classes = self._current()
        classes.update(names)
        self._commit(classes)
        return self

    def remove(self, *names):
        classes = self._current()
        classes.difference_update(names)
        self._commit(classes)
        return self

    def contains(self, name):
        return name in self._current()

    def toggle(self, name, force=None):
        classes = self._current()
        if force is None:
            if name in classes:
                classes.discard(name)
            else:
                classes.add(name)
        elif force:
            classes.add(name)
        else:
            classes.discard(name)
        self._commit(classes)
        return name in classes

    def __contains__(self, name):
        return name in self._current()

    def __iter__(self):
        return iter(sorted(self._current()))


class Node(EventTarget):
    def __init__(self, tag="div", document=None):
        super().__init__(self)
        self.tag = tag
        self._document = document
        self._parent = None
        self._attrs = {}
        self._children = []
        self._text = ""
        self._html_block = None
        self._style = _Style(self)

    @property
    def owner_document(self):
        return self._document

    @property
    def ownerDocument(self):
        return self._document

    def get_attribute(self, name):
        return self._attrs.get(name, None)

    def getAttribute(self, name):
        return self.get_attribute(name)

    def set_attribute(self, name, value):
        self._attrs[name] = str(value) if value is not None else str(value)

    def setAttribute(self, name, value):
        self.set_attribute(name, value)

    def has_attribute(self, name):
        return name in self._attrs

    def hasAttribute(self, name):
        return self.has_attribute(name)

    def remove_attribute(self, name):
        self._attrs.pop(name, None)

    def removeAttribute(self, name):
        self.remove_attribute(name)

    @property
    def attributes(self):
        return dict(self._attrs)

    @property
    def children(self):
        return list(self._children)

    def child_nodes(self):
        return list(self._children)

    def childNodes(self):
        return self.child_nodes()

    def append_child(self, child):
        child._parent = self
        child._document = self._document or child._document
        self._children.append(child)
        return child

    def appendChild(self, child):
        return self.append_child(child)

    def remove_child(self, child):
        if child in self._children:
            self._children.remove(child)
            child._parent = None
        return child

    def removeChild(self, child):
        return self.remove_child(child)

    def insert_before(self, child, reference):
        child._parent = self
        index = self._children.index(reference) if reference in self._children else len(self._children)
        self._children.insert(index, child)
        return child

    def insertBefore(self, child, reference):
        return self.insert_before(child, reference)

    def replace_child(self, new_child, old_child):
        if old_child in self._children:
            new_child._parent = self
            self._children[self._children.index(old_child)] = new_child
        return new_child

    def replaceChild(self, new_child, old_child):
        return self.replace_child(new_child, old_child)

    def remove(self):
        if self._parent is not None:
            self._parent.remove_child(self)

    def _walk(self):
        yield self
        for child in self._children:
            yield from child._walk()

    def _descendants(self):
        for child in self._children:
            yield child
            yield from child._descendants()

    @staticmethod
    def _matches(node, selector):
        selector = selector.strip()
        if selector.startswith("#"):
            return node.get_attribute("id") == selector[1:]
        if selector.startswith("."):
            classes = node.get_attribute("class") or ""
            return selector[1:] in classes.split()
        if selector.startswith("[") and selector.endswith("]"):
            return node.has_attribute(selector[1:-1])
        return node.tag.lower() == selector.lower()

    def query_selector(self, selector):
        for node in self._descendants():
            if self._matches(node, selector):
                return node
        return None

    def querySelector(self, selector):
        return self.query_selector(selector)

    def query_selector_all(self, selector):
        return [n for n in self._descendants() if self._matches(n, selector)]

    def querySelectorAll(self, selector):
        return self.query_selector_all(selector)

    def matches(self, selector):
        return self._matches(self, selector)

    def closest(self, selector):
        node = self
        while node is not None:
            if node._matches(node, selector):
                return node
            node = node._parent
        return None

    @property
    def parent_node(self):
        return self._parent

    @property
    def parentNode(self):
        return self._parent

    @property
    def tag_name(self):
        return self.tag.upper()

    @property
    def tagName(self):
        return self.tag_name

    @property
    def id(self):
        return self.get_attribute("id")

    @id.setter
    def id(self, value):
        self.set_attribute("id", value)

    @property
    def text_content(self):
        return self._html_block if self._text == "" and self._html_block else self._text

    @text_content.setter
    def text_content(self, value):
        self._text = str(value)
        self._html_block = None
        self._children = []

    @property
    def textContent(self):
        return self.text_content

    @textContent.setter
    def textContent(self, value):
        self.text_content = value

    @property
    def text(self):
        return self.text_content

    @text.setter
    def text(self, value):
        self.text_content = value

    @property
    def inner_text(self):
        return self.text_content

    @inner_text.setter
    def inner_text(self, value):
        self.text_content = value

    @property
    def innerText(self):
        return self.inner_text

    @innerText.setter
    def innerText(self, value):
        self.inner_text = value

    @property
    def inner_html(self):
        if self._html_block is not None:
            return self._html_block
        parts = []
        for child in self._children:
            parts.append(child.outer_html)
        if self._text:
            parts.append(_escape(self._text))
        return "".join(parts)

    @inner_html.setter
    def inner_html(self, value):
        self._html_block = str(value)
        self._text = ""
        self._children = []

    @property
    def innerHTML(self):
        return self.inner_html

    @innerHTML.setter
    def innerHTML(self, value):
        self.inner_html = value

    @property
    def outer_html(self):
        if not self.tag:
            return _escape(self._text)
        attrs = "".join(
            f' {k}="{_escape(v)}"' for k, v in sorted(self._attrs.items())
        )
        if self.tag.lower() in {"area", "base", "br", "col", "embed", "hr",
                                "img", "input", "link", "meta", "param",
                                "source", "track", "wbr"}:
            return f"<{self.tag}{attrs}>"
        return f"<{self.tag}{attrs}>{self.inner_html}</{self.tag}>"

    @property
    def outerHTML(self):
        return self.outer_html

    @property
    def class_name(self):
        return self.get_attribute("class") or ""

    @class_name.setter
    def class_name(self, value):
        self.set_attribute("class", value)

    @property
    def className(self):
        return self.class_name

    @className.setter
    def className(self, value):
        self.class_name = value

    @property
    def classes(self):
        return _ClassList(self)

    @property
    def classList(self):
        return self.classes

    @property
    def hidden(self):
        return self.has_attribute("hidden")

    @hidden.setter
    def hidden(self, value):
        if value:
            self.set_attribute("hidden", "")
        else:
            self.remove_attribute("hidden")

    @property
    def style(self):
        return self._style

    @property
    def value(self):
        if self.tag.lower() in {"input", "textarea", "select"}:
            return self.get_attribute("value") or ""
        return None

    @value.setter
    def value(self, new_value):
        if self.tag.lower() in {"input", "textarea", "select"}:
            self.set_attribute("value", new_value)
        elif new_value is not None:
            raise ValueError("value is only meaningful on form controls")

    def click(self):
        event = Event("click", self, {"clientX": 0, "clientY": 0, "button": 0})
        return self.dispatch_event(event)

    def focus(self):
        self.dispatch_event(Event("focus", self, {}))

    def blur(self):
        self.dispatch_event(Event("blur", self, {}))

    def scroll_into_view(self, *args):
        return None

    def scrollIntoView(self, *args):
        return None

    def get_bounding_client_rect(self):
        return {"x": 0, "y": 0, "width": 0, "height": 0, "top": 0,
                "right": 0, "bottom": 0, "left": 0}

    def getBoundingClientRect(self):
        return self.get_bounding_client_rect()

    def __getattr__(self, name):
        if name.startswith("on_") and len(name) > 3:
            event_name = name[3:].replace("_", "-")

            def register(callback, _event_name=event_name):
                self.add_event_listener(_event_name, callback)
                return callback

            return register
        raise AttributeError(name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def __str__(self):
        return self.outer_html


class Document(Node):
    def __init__(self):
        super().__init__("html", None)
        self._title = ""
        self._document = self
        self._head = Node("head", self)
        self._body = Node("body", self)
        self._children = [self._head, self._body]
        self._window = None

    def get_element_by_id(self, element_id):
        for node in self._walk():
            if node.get_attribute("id") == element_id:
                return node
        return None

    def getElementById(self, element_id):
        return self.get_element_by_id(element_id)

    def get_elements_by_tag_name(self, tag):
        tag = tag.lower()
        return [n for n in self._walk() if n.tag.lower() == tag]

    def getElementsByTagName(self, tag):
        return self.get_elements_by_tag_name(tag)

    def create_element(self, tag):
        return Node(tag, self)

    def createElement(self, tag):
        return self.create_element(tag)

    def create_text_node(self, text):
        node = Node("", self)
        node._text = str(text)
        return node

    def createTextNode(self, text):
        return self.create_text_node(text)

    @property
    def head(self):
        return self._head

    @property
    def body(self):
        return self._body

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        self._title = str(value)

    @property
    def ready_state(self):
        return "complete"

    @property
    def readyState(self):
        return "complete"

    @property
    def default_view(self):
        return self._window

    @property
    def defaultView(self):
        return self._window

    def write(self, *chunks):
        self._body.append_child(Node("", self))._text = " ".join(str(c) for c in chunks)


class Console:
    def __init__(self, window):
        self._window = window

    def _emit(self, level, args):
        text = " ".join(str(a) for a in args)
        if _bridge.enabled():
            native = _bridge.native()
            emit = getattr(native, "console_log", None)
            if emit is not None:
                emit(level, text)
        print(text)

    def log(self, *args):
        self._emit("log", args)

    def info(self, *args):
        self._emit("info", args)

    def warn(self, *args):
        self._emit("warn", args)

    def error(self, *args):
        self._emit("error", args)

    def debug(self, *args):
        self._emit("debug", args)

    def dir(self, *args):
        self._emit("dir", args)

    def assert_(self, condition, *args):
        if not condition:
            self._emit("assert", ("Assertion failed:", *args))

    def table(self, *args):
        self._emit("table", args)

    def clear(self):
        self._emit("clear", ())

    def __getattr__(self, name):
        if name in ("assert",):
            return self.assert_
        raise AttributeError(name)


class Navigator:
    def __init__(self, window):
        self.user_agent = "Pymium"
        self.platform = "Pymium"
        self.language = "en-US"
        self.on_line = True

    @property
    def userAgent(self):
        return self.user_agent

    @property
    def onLine(self):
        return self.on_line


class Location:
    def __init__(self, window):
        self.href = "about:blank"
        self.protocol = "about:"
        self.host = ""
        self.hostname = ""
        self.port = ""
        self.pathname = ""
        self.search = ""
        self.hash = ""

    def assign(self, url):
        self.href = str(url)

    def replace(self, url):
        self.href = str(url)

    def reload(self, *_args):
        return None


class History:
    def __init__(self, window):
        self.length = 0

    def back(self):
        return None

    def forward(self):
        return None

    def go(self, _delta=0):
        return None


class Window(EventTarget):
    def __init__(self):
        super().__init__(self)
        self._document = Document()
        self._document._window = self
        self._console = Console(self)
        self._navigator = Navigator(self)
        self._location = Location(self)
        self._history = History(self)
        self._timers = set()

    @property
    def document(self):
        return self._document

    @property
    def console(self):
        return self._console

    @property
    def navigator(self):
        return self._navigator

    @property
    def location(self):
        return self._location

    @property
    def history(self):
        return self._history

    @property
    def onload(self):
        return None

    @onload.setter
    def onload(self, callback):
        if callback is not None:
            self.addEventListener("load", callback)

    def alert(self, message=""):
        self.console.log(f"[pymium alert] {message}")

    def confirm(self, message=""):
        return True

    def prompt(self, message="", default_value=""):
        return default_value

    def open(self, url=None, *_args):
        return None

    def close(self):
        return None

    def _safe_call(self, fn, *args):
        try:
            return fn(*args)
        except Exception as exc:  # noqa: BLE001
            self.console.error(f"uncaught python error in async call: {exc!r}")

    def set_timeout(self, callback, ms):
        timer = threading.Timer(max(ms, 0) / 1000.0, self._safe_call,
                                args=(callback,))
        timer.start()
        return timer

    def setTimeout(self, callback, ms):
        return self.set_timeout(callback, ms)

    def clear_timeout(self, timer):
        if timer is not None:
            timer.cancel()

    def clearTimeout(self, timer):
        self.clear_timeout(timer)

    def set_interval(self, callback, ms):
        stop = threading.Event()

        def loop():
            while not stop.wait(max(ms, 0) / 1000.0):
                self._safe_call(callback)

        thread = threading.Thread(target=loop, daemon=True)
        thread.start()
        return stop

    def setInterval(self, callback, ms):
        return self.set_interval(callback, ms)

    def clear_interval(self, stop_event):
        if stop_event is not None:
            stop_event.set()

    def clearInterval(self, stop_event):
        self.clear_interval(stop_event)

    def request_animation_frame(self, callback):
        return self.set_timeout(lambda: self._safe_call(callback), 0)

    def requestAnimationFrame(self, callback):
        return self.request_animation_frame(callback)


window = Window()
document = window.document
console = window.console
navigator = window.navigator
location = window.location
history = window.history

__all__ = [
    "window",
    "document",
    "console",
    "navigator",
    "location",
    "history",
    "Node",
    "Document",
    "Window",
    "Console",
    "Navigator",
    "Location",
    "History",
]