"""
Element inspection: collect tag, attributes, and text preview from a DOM element in the browser.
Used by the picker to pass structured "inner details" to the element-options dialog.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Max lengths for preview strings (matches docs/picker/picker-enhancement.md)
INNER_TEXT_PREVIEW_LEN = 80
HTML_PREVIEW_LEN = 200


@dataclass
class ElementInspection:
    """
    Structured payload for a selected DOM element.
    Fetched in the browser and passed to the GUI for pre-filling dropdowns.
    """
    tag_name: str
    attributes: List[Dict[str, str]]  # [{"name": "href", "value": "https://..."}, ...]
    inner_text_preview: str
    html_preview: str
    selector: str

    @classmethod
    def from_browser_dict(cls, data: Dict[str, Any]) -> Optional["ElementInspection"]:
        """Build from the object returned by the browser (JS). Returns None if invalid."""
        if not data or not isinstance(data, dict):
            return None
        selector = data.get("selector")
        if not selector or not isinstance(selector, str):
            return None
        tag_name = data.get("tagName") or data.get("tag_name") or ""
        if not isinstance(tag_name, str):
            tag_name = str(tag_name)
        attrs = data.get("attributes")
        if not isinstance(attrs, list):
            attrs = []
        normalized_attrs: List[Dict[str, str]] = []
        for a in attrs:
            if isinstance(a, dict) and "name" in a and "value" in a:
                normalized_attrs.append({
                    "name": str(a["name"]),
                    "value": str(a["value"]),
                })
        inner = data.get("innerTextPreview") or data.get("inner_text_preview") or ""
        html = data.get("htmlPreview") or data.get("html_preview") or ""
        return cls(
            tag_name=tag_name,
            attributes=normalized_attrs,
            inner_text_preview=str(inner)[:INNER_TEXT_PREVIEW_LEN],
            html_preview=str(html)[:HTML_PREVIEW_LEN],
            selector=selector,
        )


def get_element_inspection_js() -> str:
    """
    Return JavaScript that defines window.__getInspection(el).
    Given a DOM element, returns { selector, tagName, attributes, innerTextPreview, htmlPreview }.
    Must be evaluated after get_selector_for_element_js() so window.__getSelector exists.
    """
    return r"""
(function() {
  function getInspection(el) {
    if (!el || !el.tagName) return null;
    var selector = typeof window.__getSelector === 'function' ? window.__getSelector(el) : '';
    var tagName = el.tagName.toLowerCase();
    var attributes = [];
    if (el.attributes) {
      for (var i = 0; i < el.attributes.length; i++) {
        var a = el.attributes[i];
        attributes.push({ name: a.name, value: a.value || '' });
      }
    }
    var innerText = (el.innerText || el.textContent || '').trim();
    var innerTextPreview = innerText.length > 80 ? innerText.slice(0, 80) + '...' : innerText;
    var html = (el.outerHTML || '');
    var htmlPreview = html.length > 200 ? html.slice(0, 200) + '...' : html;
    return {
      selector: selector,
      tagName: tagName,
      attributes: attributes,
      innerTextPreview: innerTextPreview,
      htmlPreview: htmlPreview
    };
  }
  window.__getInspection = getInspection;
})();
""".strip()
