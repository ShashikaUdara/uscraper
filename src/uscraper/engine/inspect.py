"""
Element inspection: collect tag, attributes, and text preview from a DOM element in the browser.
Used by the picker to pass structured "inner details" to the element-options dialog.
Phase 5b: full element hierarchy (path from root, clicked node, optional children).
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Max lengths for preview strings (matches docs/picker/picker-enhancement.md)
INNER_TEXT_PREVIEW_LEN = 80
HTML_PREVIEW_LEN = 200
# Phase 5b: per-node text/attr preview caps for hierarchy
HIERARCHY_TEXT_PREVIEW_LEN = 40
HIERARCHY_ATTR_VALUE_LEN = 60


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


@dataclass
class HierarchyNode:
    """One node in the element hierarchy (path from root or child). Phase 5b."""
    tag_name: str
    id: str  # noqa: A001
    class_name: str
    attributes: List[Dict[str, str]]
    text_preview: str

    @classmethod
    def from_browser_dict(cls, data: Dict[str, Any]) -> "HierarchyNode":
        if not data or not isinstance(data, dict):
            return cls(tag_name="", id="", class_name="", attributes=[], text_preview="")
        tag = (data.get("tagName") or data.get("tag_name") or "")
        id_val = str(data.get("id") or "")
        class_val = str(data.get("className") or data.get("class_name") or "")
        attrs = data.get("attributes")
        if not isinstance(attrs, list):
            attrs = []
        norm: List[Dict[str, str]] = []
        for a in attrs:
            if isinstance(a, dict) and "name" in a:
                v = str(a.get("value") or "")[:HIERARCHY_ATTR_VALUE_LEN]
                norm.append({"name": str(a["name"]), "value": v})
        text = str(data.get("textPreview") or data.get("text_preview") or "")[:HIERARCHY_TEXT_PREVIEW_LEN]
        return cls(tag_name=tag, id=id_val, class_name=class_val, attributes=norm, text_preview=text)


@dataclass
class ElementHierarchy:
    """Full hierarchy for the clicked element: path from root, clicked node, optional children. Phase 5b."""
    path_from_root: List[HierarchyNode]
    clicked_node: HierarchyNode
    children: List[HierarchyNode]

    @classmethod
    def from_browser_dict(cls, data: Dict[str, Any]) -> Optional["ElementHierarchy"]:
        if not data or not isinstance(data, dict):
            return None
        path = data.get("pathFromRoot") or data.get("path_from_root")
        if not isinstance(path, list):
            path = []
        clicked = data.get("clickedNode") or data.get("clicked_node")
        if not clicked or not isinstance(clicked, dict):
            clicked = {}
        children = data.get("children")
        if not isinstance(children, list):
            children = []
        path_nodes = [HierarchyNode.from_browser_dict(n) for n in path]
        clicked_node = HierarchyNode.from_browser_dict(clicked)
        child_nodes = [HierarchyNode.from_browser_dict(c) for c in children]
        return cls(path_from_root=path_nodes, clicked_node=clicked_node, children=child_nodes)


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


def get_element_hierarchy_js() -> str:
    """
    Return JavaScript that defines window.__getHierarchy(el). Phase 5b.
    Given a DOM element, returns { pathFromRoot, clickedNode, children }.
    pathFromRoot: nodes from body down to el (tagName, id, className, attributes, textPreview).
    clickedNode: full details for el. children: first-level children (tag + key attrs).
    Must be evaluated after get_selector_for_element_js() so we can use the same node format.
    """
    return r"""
(function() {
  var TEXT_LEN = 40, ATTR_LEN = 60;
  function nodeData(el) {
    if (!el || el.nodeType !== 1) return null;
    var tagName = (el.tagName || '').toLowerCase();
    var id = (el.id || '');
    var className = (el.className && typeof el.className === 'string') ? el.className : '';
    var attributes = [];
    if (el.attributes) {
      for (var i = 0; i < el.attributes.length; i++) {
        var a = el.attributes[i];
        var v = (a.value || '').slice(0, ATTR_LEN);
        attributes.push({ name: a.name, value: v });
      }
    }
    var text = (el.innerText || el.textContent || '').trim().slice(0, TEXT_LEN);
    return { tagName: tagName, id: id, className: className, attributes: attributes, textPreview: text };
  }
  function getHierarchy(el) {
    if (!el || !el.tagName) return null;
    var pathFromRoot = [];
    var current = el;
    while (current && current.nodeType === 1) {
      pathFromRoot.unshift(nodeData(current));
      current = current.parentElement;
    }
    var clickedNode = nodeData(el);
    var inner = (el.innerText || el.textContent || '').trim();
    clickedNode.textPreview = inner.length > 80 ? inner.slice(0, 80) + '...' : inner;
    var children = [];
    if (el.children) {
      for (var j = 0; j < Math.min(el.children.length, 20); j++) {
        children.push(nodeData(el.children[j]));
      }
    }
    return { pathFromRoot: pathFromRoot, clickedNode: clickedNode, children: children };
  }
  window.__getHierarchy = getHierarchy;
})();
""".strip()
