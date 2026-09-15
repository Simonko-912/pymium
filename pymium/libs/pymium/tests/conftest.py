import pytest

from pymium import browser


@pytest.fixture(autouse=True)
def _fresh_page():
    browser.document._body._children.clear()
    browser.document._head._children.clear()
    yield