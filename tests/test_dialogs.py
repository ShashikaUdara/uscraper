"""Tests for dialog helpers: column suggestions and extract/attr suggestions (Phase 4b)."""
import pytest

from uscraper.engine.inspect import ElementInspection
from uscraper.gui.dialogs import _column_suggestions, _suggest_extract_and_attr


def _inspection(tag: str, attributes: list) -> ElementInspection:
    return ElementInspection(
        tag_name=tag,
        attributes=attributes,
        inner_text_preview="",
        html_preview="",
        selector="x",
    )


def test_column_suggestions_a_href():
    insp = _inspection("a", [{"name": "href", "value": "https://example.com"}])
    opts, default = _column_suggestions(insp)
    assert "link" in opts
    assert default == "link"
    assert "inner_text" in opts
    assert "html" in opts


def test_column_suggestions_img_src():
    insp = _inspection("img", [{"name": "src", "value": "/x.png"}, {"name": "alt", "value": "Y"}])
    opts, default = _column_suggestions(insp)
    assert "image_src" in opts
    assert "image_alt" in opts
    assert default == "image_src"


def test_column_suggestions_generic_tag_attr():
    insp = _inspection("span", [{"name": "class", "value": "nav"}])
    opts, default = _column_suggestions(insp)
    assert "span_class" in opts
    assert default == "span_class"
    assert "inner_text" in opts


def test_column_suggestions_with_existing_columns():
    insp = _inspection("a", [{"name": "href", "value": "u"}])
    opts, _ = _column_suggestions(insp, existing_columns=["title", "link"])
    assert "link" in opts
    assert "title" in opts
    assert opts.count("link") == 1


def test_column_suggestions_no_inspection():
    opts, default = _column_suggestions(None)
    assert "inner_text" in opts
    assert "html" in opts
    assert default in opts


def test_column_suggestions_no_inspection_with_existing():
    opts, default = _column_suggestions(None, existing_columns=["col1"])
    assert "col1" in opts
    assert "inner_text" in opts
    assert default == "col1"


def test_suggest_extract_and_attr_a_href():
    insp = _inspection("a", [{"name": "href", "value": "https://x"}])
    ext, attr = _suggest_extract_and_attr(insp)
    assert ext == "attribute"
    assert attr == "href"


def test_suggest_extract_and_attr_img_src():
    insp = _inspection("img", [{"name": "src", "value": "/a.png"}])
    ext, attr = _suggest_extract_and_attr(insp)
    assert ext == "attribute"
    assert attr == "src"


def test_suggest_extract_and_attr_text_fallback():
    insp = _inspection("div", [])
    ext, attr = _suggest_extract_and_attr(insp)
    assert ext == "text"
    assert attr is None
    ext2, attr2 = _suggest_extract_and_attr(None)
    assert ext2 == "text"
    assert attr2 is None
