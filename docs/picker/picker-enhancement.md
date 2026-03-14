# Picker Enhancement: Element Details and User-Friendly Selection

This document describes the approach, UX improvements, and implementation plan for enhancing the element picker so that when a user selects an element, **all relevant inner details are surfaced in the UI** (including dropdowns populated with the element’s attributes and values), making the picker more informative and easier to use.

---

## 1. Goals

- **Show element “inner details” in the UI**: When an element is selected, display its tag name, attributes (name → value), text preview, and other useful metadata.
- **Dropdowns with real values**: Populate dropdowns (e.g. column name, attribute to extract) from the selected element’s actual attributes and values instead of free-text only.
- **Better defaults**: Suggest column name and extract type/attribute based on the element (e.g. `<a href="...">` → column “link”, extract “attribute”, attribute “href”).
- **Clearer UX**: Preview selector, tag, and a short text/HTML snippet so the user can confirm they picked the right node.

---

## 2. What “Inner Details” Means

For the **selected DOM element**, we consider the following as “inner details” to collect and show:

| Detail | Description | Use in UI |
|--------|-------------|-----------|
| **Tag name** | e.g. `a`, `div`, `img`, `span` | Label, column-name suggestion |
| **Attributes** | All attributes as `name → value` (e.g. `href`, `src`, `class`, `id`, `data-*`) | Dropdown for “attribute to extract”; show value next to name |
| **Inner text** | First N characters of `innerText` or `textContent` | Preview so user confirms the right element |
| **HTML snippet** | Short outer HTML (e.g. first 200 chars) | Optional preview in dialog |
| **Computed role/label** | Optional: `aria-label`, `title`, `alt` | Suggestions for column name |
| **Selector** | Stable CSS selector (already computed) | Show full selector, copy button |

These will be **fetched in the browser** (via a small script run on the page) when the user clicks an element, then passed to the desktop app so the element-options dialog can pre-fill and populate dropdowns.

---

## 3. Approach and Ways to Make the Picker More User-Friendly

### 3.1 Element Inspection (Data from the Page)

- **When**: Right after the user clicks an element (or when the “element options” dialog is about to open).
- **How**: Run a small JavaScript snippet in the page that, given the clicked element, returns a structured object:
  - `tagName`
  - `attributes`: list of `{ name, value }` (or object `{ attrName: attrValue }`)
  - `innerTextPreview` (e.g. first 80 chars)
  - `htmlPreview` (optional, first 200 chars of `outerHTML`)
  - `selector` (already available from existing picker flow)
- **Where**: Implement in the picker/engine layer (e.g. a function that runs in Playwright after a click and returns this payload to the GUI).

### 3.2 Element Options Dialog Enhancements

- **Selector**
  - Show full selector with optional “Copy” button.
  - Optionally show a short “readable” form (e.g. tag + id/class) for clarity.

- **Column name**
  - **Dropdown + free text**: Pre-populate choices from:
    - Suggested names derived from the element (e.g. “link”, “image_src”, “title”) from tag + important attributes.
    - Existing column names already in the profile (to avoid duplicates and keep naming consistent).
  - Allow typing a custom name (combobox behaviour).
  - Default suggestion: e.g. `tagName` + first attribute name (e.g. `a_href`, `img_src`).

- **Extract type**
  - Keep: **text** | **attribute** | **html**.
  - When “attribute” is selected, show the **attribute dropdown** (see below).

- **Attribute name (when extract type = attribute)**
  - **Dropdown** of the element’s **actual attribute names**, each showing the attribute value (e.g. `href → https://example.com/page`).
  - Values can be truncated in the label (e.g. 40 chars) with tooltip for full value.
  - If the element has no attributes, show a message and allow manual entry for edge cases.

### 3.3 Preview and Confirmation

- **Element preview**
  - One line: tag + id/class if present (e.g. `a#main-link.nav-item`).
  - One line: inner text preview (e.g. “Click here to go to…”).
  - Reduces mistakes when many similar elements exist on the page.

### 3.4 Workflow and Responsiveness

- **Non-blocking inspection**: If inspection is done when the dialog opens, keep it fast (single `page.evaluate`); if needed, show “Loading…” for that part only.
- **Re-select**: Allow “Pick again” from the dialog to re-run the picker for the same profile/URL without closing the dialog (optional, can be a later phase).
- **Keyboard**: Enter to confirm, Escape to cancel (standard for modal dialogs).

### 3.5 Accessibility and Edge Cases

- **No attributes**: If the element has no attributes, attribute dropdown is empty; allow manual entry for “attribute” extract type (e.g. for dynamic attributes).
- **Duplicate column names**: Warn if the chosen column name already exists in the profile.
- **Long values**: Truncate in dropdowns; show full value in tooltip or a small “View full” area.



---

**Implementation plan, picker usability (hover, full hierarchy, scrape-all-matching), summary table, dependencies, and future enhancements** have been moved to **docs/picker/scraping-flow.md** (Sections 4–8). This document (picker-enhancement.md) now focuses on goals, inner details, and the approach for the element-options dialog; the full implementation plan and picker UX flow live in scraping-flow.md.
