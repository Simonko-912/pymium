"""Pythonic API: snake_case, decorators, `with` blocks, text/classes/style."""
from pymium.browser import document, window
from pymium.events import Event
from pymium import html


def test_on_click_decorator():
    el = document.createElement("button")
    clicks = []

    @el.on_click
    def handler(event):
        clicks.append((event.type, event.clientX, event.target is el))

    el.click()
    assert clicks == [("click", 0, True)]
    el.click()
    assert len(clicks) == 2


def test_on_alias_and_event_target():
    el = document.createElement("div")
    seen = []

    @el.on("mouseenter")
    def enter(event):
        seen.append(event.type)

    el.dispatchEvent(Event("mouseenter", el))
    assert seen == ["mouseenter"]


def test_once_handlers():
    el = document.createElement("button")
    hits = []
    el.addEventListener("click", lambda e: hits.append(1), once=True)
    el.click()
    el.click()
    assert hits == [1]


def test_with_element_bulk_edit():
    el = document.createElement("div")
    with el:
        el.text = "on"
        el.hidden = True
    assert el.text == "on"
    assert el.hidden is True


def test_pythonic_classes():
    el = document.createElement("div")
    el.classes.add("a", "b")
    assert el.classes.contains("a")
    assert "b" in el.classes
    el.classes.toggle("a")
    assert not el.classes.contains("a")
    el.classes.remove("b")
    assert list(el.classes) == []


def test_pythonic_style_and_text():
    el = document.createElement("div")
    el.style.font_size = "14px"
    assert el.style.get_property_value("font-size") == "14px"
    el.text = "hi"
    assert el.inner_text == "hi"
    assert el.innerText == "hi"


def test_python_globals_shape():
    from pymium import page_globals
    globals_dict = page_globals()
    assert set(["window", "document", "console", "navigator", "location",
                "history", "Event", "EventTarget", "python"]).issubset(
                    globals_dict)
    assert globals_dict["window"] is window
    assert globals_dict["document"] is document


def test_pythonic_markup_composition():
    out = html.ul(
        [html.li(item) for item in ("one", "two")],
        cls="menu",
    )
    assert out == '<ul class="menu">' \
                  '<li>one</li><li>two</li></ul>'


def test_default_prevented():
    el = document.createElement("a")
    outcome = {}

    @el.on("click")
    def handler(event):
        event.preventDefault()
        outcome["prevented"] = event.default_prevented

    el.click()
    assert outcome["prevented"] is True