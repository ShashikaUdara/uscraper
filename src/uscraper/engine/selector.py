"""
Selector generation: compute a stable CSS selector for a DOM element.
Used by the element picker when the user clicks an element.
"""
from typing import Optional

# JavaScript that, when evaluated in the page, defines window.__getSelector(el).
# Uses id if unique (with CSS.escape), else builds path from root using tag:nth-child(n).
GET_SELECTOR_JS = r"""
(function() {
  var escapeId = typeof CSS !== 'undefined' && CSS.escape ? function(id) { return CSS.escape(id); } : function(id) {
    return ('' + id).replace(/([.#:[\]])/g, '\\$1');
  };
  function getSelector(el) {
    if (!el || !el.tagName) return '';
    if (el.id) {
      try {
        var idSel = '#' + escapeId(el.id);
        if (document.querySelectorAll(idSel).length === 1) return idSel;
      } catch (e) {}
    }
    var path = [];
    var current = el;
    while (current && current.nodeType === 1) {
      var tag = current.tagName.toLowerCase();
      var parent = current.parentElement;
      if (!parent) { path.unshift(tag); break; }
      var idx = 0;
      for (var i = 0; i < parent.children.length; i++) {
        if (parent.children[i] === current) {
          idx = i + 1;
          path.unshift(tag + ':nth-child(' + idx + ')');
          break;
        }
      }
      current = parent;
    }
    return path.join(' > ');
  }
  window.__getSelector = getSelector;
})();
"""


def get_selector_for_element_js() -> str:
    """
    Return the JavaScript source that defines window.__getSelector(el).
    After evaluating this in a page, call page.evaluate('window.__getSelector(document.querySelector(...))')
    or pass an element handle from the page.
    """
    return GET_SELECTOR_JS.strip()


def compute_selector_via_page(page, element_handle) -> Optional[str]:
    """
    Given a Playwright page and an ElementHandle, compute a CSS selector for that element
    by evaluating the injected getSelector in the page with the element.
    """
    try:
        selector = element_handle.evaluate("""(el) => {
          if (typeof window.__getSelector === 'function')
            return window.__getSelector(el);
          return '';
        }""")
        return selector if isinstance(selector, str) and selector else None
    except Exception:
        return None
