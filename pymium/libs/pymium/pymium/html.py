"""Author markup from Python, JSX-style.

>>> innerHTML = div(cls="box", children=...)
"""
import html as _stdlib_html

_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
         "link", "meta", "param", "source", "track", "wbr"}


class _Markup(str):
    """A pre-rendered fragment; children that are _Markup are inserted raw,
    plain strings are escaped. `h` and `markup` always return _Markup."""


def escape(text):
    return _stdlib_html.escape(str(text), quote=False)


def _stringify(child):
    if child is None or child is False or child is True:
        return ""
    if child == 0:
        return "0"
    if isinstance(child, _Markup):
        return str(child)
    if isinstance(child, (list, tuple)):
        return "".join(_stringify(item) for item in child)
    return escape(child)


def h(tag, *children, **attrs):
    parts = [f"<{tag}"]
    for key, value in attrs.items():
        if value is None or value is False:
            continue
        if key in ("cls", "klass"):
            key = "class"
        key = key.replace("_", "-")
        parts.append(f' {key}="{escape(value)}"')
    opening = "".join(parts)
    if tag.lower() in _VOID:
        return _Markup(f"{opening}>")
    body = "".join(_stringify(child) for child in children)
    return _Markup(f"{opening}>{body}</{tag}>")


def markup(*parts):
    return _Markup("".join(_stringify(part) for part in parts))


_TAGS = [
    "a", "article", "aside", "b", "blockquote", "br", "button", "canvas",
    "code", "dd", "div", "dl", "dt", "em", "fieldset", "figcaption",
    "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6",
    "header", "hr", "i", "iframe", "img", "input", "label", "legend", "li",
    "main", "nav", "ol", "optgroup", "option", "p", "pre", "section",
    "select", "small", "span", "strong", "sub", "sup", "table", "tbody",
    "td", "textarea", "tfoot", "th", "thead", "tr", "ul", "video",
]


def _make_tag(tag):
    def builder(*children, **attrs):
        return h(tag, *children, **attrs)

    builder.__name__ = tag
    builder.__qualname__ = tag
    return builder


globals().update({tag: _make_tag(tag) for tag in _TAGS})

__all__ = ["h", "markup", "escape"] + _TAGS