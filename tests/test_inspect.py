"""Tests for element inspection: ElementInspection, hierarchy (Phase 5b), get_element_inspection_js."""
import pytest

from uscraper.engine.inspect import (
    ElementHierarchy,
    ElementInspection,
    HierarchyNode,
    get_element_hierarchy_js,
    get_element_inspection_js,
    INNER_TEXT_PREVIEW_LEN,
    HTML_PREVIEW_LEN,
)


def test_get_element_inspection_js_returns_non_empty():
    js = get_element_inspection_js()
    assert isinstance(js, str)
    assert "__getInspection" in js
    assert "tagName" in js
    assert "attributes" in js
    assert "innerTextPreview" in js
    assert "htmlPreview" in js
    assert len(js) > 100


def test_from_browser_dict_valid():
    data = {
        "selector": "a#x.nav",
        "tagName": "a",
        "attributes": [
            {"name": "href", "value": "https://example.com"},
            {"name": "class", "value": "nav"},
        ],
        "innerTextPreview": "Click here",
        "htmlPreview": "<a id=\"x\" class=\"nav\" href=\"https://example.com\">Click</a>",
    }
    insp = ElementInspection.from_browser_dict(data)
    assert insp is not None
    assert insp.selector == "a#x.nav"
    assert insp.tag_name == "a"
    assert len(insp.attributes) == 2
    assert insp.attributes[0]["name"] == "href" and insp.attributes[0]["value"] == "https://example.com"
    assert insp.attributes[1]["name"] == "class" and insp.attributes[1]["value"] == "nav"
    assert insp.inner_text_preview == "Click here"
    assert "htmlPreview" in insp.html_preview or "href" in insp.html_preview


def test_from_browser_dict_truncates_previews():
    data = {
        "selector": "#x",
        "tagName": "span",
        "attributes": [],
        "innerTextPreview": "a" * 200,
        "htmlPreview": "b" * 300,
    }
    insp = ElementInspection.from_browser_dict(data)
    assert insp is not None
    assert len(insp.inner_text_preview) <= INNER_TEXT_PREVIEW_LEN
    assert len(insp.html_preview) <= HTML_PREVIEW_LEN


def test_from_browser_dict_alternate_keys():
    """JS may send tag_name / inner_text_preview (snake_case); we accept both."""
    data = {
        "selector": "div",
        "tag_name": "div",
        "attributes": [],
        "inner_text_preview": "text",
        "html_preview": "<div>text</div>",
    }
    insp = ElementInspection.from_browser_dict(data)
    assert insp is not None
    assert insp.tag_name == "div"
    assert insp.inner_text_preview == "text"


def test_from_browser_dict_missing_selector_returns_none():
    assert ElementInspection.from_browser_dict({}) is None
    assert ElementInspection.from_browser_dict({"tagName": "a"}) is None
    assert ElementInspection.from_browser_dict({"selector": ""}) is None


def test_from_browser_dict_invalid_returns_none():
    assert ElementInspection.from_browser_dict(None) is None
    assert ElementInspection.from_browser_dict("string") is None
    assert ElementInspection.from_browser_dict([]) is None


def test_from_browser_dict_skips_invalid_attributes():
    data = {
        "selector": "a",
        "tagName": "a",
        "attributes": [
            {"name": "href", "value": "u"},
            {"name": "x"},  # missing value
            "not a dict",
            {"name": "y", "value": "v"},
        ],
        "innerTextPreview": "",
        "htmlPreview": "",
    }
    insp = ElementInspection.from_browser_dict(data)
    assert insp is not None
    assert len(insp.attributes) == 2
    assert insp.attributes[0]["name"] == "href"
    assert insp.attributes[1]["name"] == "y"


# --- Phase 5b: hierarchy ---


def test_get_element_hierarchy_js_returns_expected():
    js = get_element_hierarchy_js()
    assert isinstance(js, str)
    assert "__getHierarchy" in js
    assert "pathFromRoot" in js
    assert "clickedNode" in js
    assert "children" in js
    assert len(js) > 150


def test_hierarchy_node_from_browser_dict():
    data = {"tagName": "a", "id": "x", "className": "nav link", "attributes": [{"name": "href", "value": "u"}], "textPreview": "Click"}
    node = HierarchyNode.from_browser_dict(data)
    assert node.tag_name == "a"
    assert node.id == "x"
    assert node.class_name == "nav link"
    assert len(node.attributes) == 1
    assert node.attributes[0]["name"] == "href"
    assert node.text_preview == "Click"


def test_element_hierarchy_from_browser_dict():
    data = {
        "pathFromRoot": [
            {"tagName": "html", "id": "", "className": "", "attributes": [], "textPreview": ""},
            {"tagName": "body", "id": "", "className": "", "attributes": [], "textPreview": ""},
            {"tagName": "a", "id": "m", "className": "nav", "attributes": [{"name": "href", "value": "u"}], "textPreview": "Link"},
        ],
        "clickedNode": {"tagName": "a", "id": "m", "className": "nav", "attributes": [{"name": "href", "value": "u"}], "textPreview": "Link"},
        "children": [{"tagName": "span", "id": "", "className": "", "attributes": [], "textPreview": "x"}],
    }
    h = ElementHierarchy.from_browser_dict(data)
    assert h is not None
    assert len(h.path_from_root) == 3
    assert h.path_from_root[0].tag_name == "html"
    assert h.path_from_root[2].tag_name == "a"
    assert h.clicked_node.tag_name == "a"
    assert h.clicked_node.id == "m"
    assert len(h.children) == 1
    assert h.children[0].tag_name == "span"


def test_element_hierarchy_from_browser_dict_none_or_invalid():
    assert ElementHierarchy.from_browser_dict(None) is None
    assert ElementHierarchy.from_browser_dict("not a dict") is None
