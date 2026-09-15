"""Browser-style API: methods and attribute names mirror JavaScript."""
from pymium.browser import document
from pymium import html


def test_get_element_by_id_both_spellings():
    container = document.createElement("div")
    target = document.createElement("p")
    target.id = "greeting"
    container.appendChild(target)
    document.body.appendChild(container)

    assert document.getElementById("greeting") is target
    assert document.get_element_by_id("greeting") is target
    assert document.getElementById("missing") is None


def test_create_element_and_append():
    el = document.createElement("li")
    el.textContent = "first"
    ul = document.createElement("ul")
    ul.appendChild(el)
    assert ul.childNodes()[0] is el
    assert ul.children[0].tagName == "LI"


def test_inner_html_roundtrip():
    el = document.createElement("div")
    el.innerHTML = "<b>bold</b>"
    assert el.innerHTML == "<b>bold</b>"
    assert el.innerHTML  # non-empty
    el.innerHTML = ""
    assert el.innerHTML == ""


def test_attributes():
    el = document.createElement("a")
    el.setAttribute("href", "https://example.org")
    assert el.getAttribute("href") == "https://example.org"
    assert el.hasAttribute("href")
    el.removeAttribute("href")
    assert not el.hasAttribute("href")
    assert el.has_attribute("href") is False


def test_class_name_and_class_list_sync():
    el = document.createElement("div")
    el.className = "card wide"
    assert el.className == "card wide"
    assert el.classList.contains("card")


def test_query_selector_traversal():
    el = document.createElement("div")
    child = document.createElement("span", )
    inner = document.createElement("i")
    # tag/class selector matching is attribute-based for spans with a marker
    child.setAttribute("data-marker", "1")
    child.appendChild(inner)
    el.appendChild(child)
    document.body.appendChild(el)

    found = document.querySelector("div")
    assert found is el
    assert found.querySelector("span") is child
    assert found.querySelector("div") is None


def test_text_content_alias():
    el = document.createElement("span")
    el.textContent = "hello"
    assert el.textContent == "hello"
    assert el.textContent == el.innerText
    assert el.textContent == el.text


def test_style_property_both_spellings():
    el = document.createElement("div")
    el.style.setProperty("font-size", "14px")
    assert el.style.getPropertyValue("font-size") == "14px"
    el.style.margin_top = "2px"
    assert el.style.getPropertyValue("margin-top") == "2px"
    expected = "font-size: 14px; margin-top: 2px"
    assert el.style.cssText == expected


def test_outer_html_roundtrip():
    el = document.createElement("div")
    el.id = "box"
    el.className = "c1 c2"
    child = document.createElement("p")
    child.text = "hi"
    el.appendChild(child)
    html_text = el.outerHTML
    assert html_text.startswith("<div")
    assert 'id="box"' in html_text
    assert 'class="c1 c2"' in html_text
    assert "<p>hi</p>" in html_text


def test_markup_helpers():
    out = html.div(html.p("hello", cls="lead"), id="wrap")
    assert out == '<div id="wrap"><p class="lead">hello</p></div>'
    assert html.escape("<script>") == "&lt;script&gt;"


def test_remove_and_remove_child():
    parent = document.createElement("div")
    child = document.createElement("p")
    parent.appendChild(child)
    parent.removeChild(child)
    assert parent.children == []
    orphan = document.createElement("span")
    parent.appendChild(orphan)
    orphan.remove()
    assert parent.children == []


def test_hidden_and_value():
    el = document.createElement("div")
    assert el.hidden is False
    el.hidden = True
    assert el.hidden is True

    inp = document.createElement("input")
    inp.value = "hunter2"
    assert inp.getAttribute("value") == "hunter2"
    assert inp.value == "hunter2"