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

## 4. Implementation Plan

The work is split into **phases** so that each deliverable is testable and can be merged incrementally.

---

### Phase 4a: Element Inspection (Data Collection in Browser)

**Objective**: From the picker, when the user clicks an element, collect a structured payload (tag, attributes, text preview, selector) in the browser and pass it to the application.

**Tasks**:

1. **Define inspection payload (contract)**
   - Add a documented structure, e.g.:
     - `tagName: str`
     - `attributes: List[Dict[str, str]]` with `name` and `value`
     - `innerTextPreview: str` (max length, e.g. 80)
     - `htmlPreview: str` (optional, max length, e.g. 200)
     - `selector: str` (existing)
   - Document this in code (dataclass or typed dict) and in this doc.

2. **Implement JS snippet for inspection**
   - In `engine/selector.py` (or new `engine/inspect.py`), add a function that returns a string of JavaScript.
   - The script, given an element reference (or run in context of the clicked element), returns the payload object.
   - Example logic:
     - `tagName = element.tagName.toLowerCase()`
     - `attributes = Array.from(element.attributes).map(a => ({ name: a.name, value: a.value }))`
     - `innerTextPreview = element.innerText.slice(0, 80)` (or textContent)
     - `selector` can be taken from existing `window.__getSelector(element)` after init script.

3. **Integrate inspection into picker flow**
   - When a click is detected and a selector is obtained, run the inspection script for the same element (e.g. `document.querySelector(selector)` then run the inspector).
   - Ensure the inspector runs in the same page context; handle errors (e.g. element no longer in DOM) and return a minimal payload on failure.

4. **Pass inspection result to GUI**
   - Extend the picker’s callback or queue payload so that the GUI receives not only `selector` but also the **inspection result** (tag, attributes, text preview, etc.).
   - Backward compatibility: if inspection is missing or fails, the dialog still receives the selector and behaves as today (no dropdowns pre-filled).

**Deliverables**: Inspection payload type, JS inspector, picker returns inspection data along with selector, tests for inspector and payload shape.

**Estimated effort**: Small (1–2 days).

---

### Phase 4b: Element Options Dialog – Pre-fill and Attribute Dropdown

**Objective**: Update the element-options dialog to accept the inspection payload and show dropdowns with the element’s real attributes and values.

**Tasks**:

1. **Dialog API**
   - Change `ask_element_options(parent, selector)` to something like `ask_element_options(parent, selector, inspection=None)` where `inspection` is the payload from Phase 4a (optional for backward compatibility).

2. **Column name**
   - Add a combobox that supports both dropdown and free text.
   - **Dropdown options**:
     - Suggested names from inspection: e.g. from tag + first meaningful attribute (`a` + `href` → “link”, `img` + `src` → “image_src”), plus optional “inner_text”, “html”.
     - Optionally: list of existing column names for this profile (requires passing `existing_columns: List[str]` into the dialog).
   - **Default**: Set the initial value to the first suggestion (e.g. “link” for `<a href="...">`).

3. **Extract type**
   - Keep existing combo: text, attribute, html.
   - When “attribute” is selected, show the attribute dropdown; when “text” or “html”, hide or disable it.

4. **Attribute dropdown**
   - When extract type is “attribute”, show a **dropdown** (or combobox) where each option is:
     - Display: `attr_name → truncated(value)` (e.g. `href → https://example.com/...`).
     - Stored value: `attr_name`.
   - Populate from `inspection.attributes`.
   - If there are no attributes, show “No attributes” and allow manual entry (optional fallback).
   - Pre-select the first attribute or a common one (e.g. `href` for `<a>`, `src` for `<img>`).

5. **Preview**
   - In the dialog, add a short “Element preview” section: tag name, optional id/class, and `innerTextPreview` in a read-only label or small text widget.

6. **Selector display**
   - Keep showing the selector; optionally add a “Copy” button that copies the full selector to the clipboard.

**Deliverables**: Updated `ask_element_options` with inspection, column suggestions, attribute dropdown with values, preview, tests (unit or manual) for dialog behaviour.

**Estimated effort**: Small–medium (1–2 days).

---

### Phase 4c: Picker–Dialog Wiring and Profile Column List

**Objective**: Wire the picker to pass inspection data into the dialog, and optionally show existing profile columns in the column-name suggestions.

**Tasks**:

1. **Picker callback payload**
   - Ensure that when the user clicks an element, the picker (engine) runs the inspector and sends `(selector, inspection)` (or equivalent) to the GUI.
   - GUI receives this and calls `ask_element_options(parent, selector, inspection=inspection)`.

2. **Existing columns**
   - When opening the element-options dialog, the main window can pass the list of column names already defined for the current profile (from `list_profile_elements` or `get_profile_with_elements`).
   - Dialog uses this to:
     - Populate “existing columns” in the column-name dropdown (so user can reuse names).
     - Optionally warn if the user picks a column name that already exists (duplicate).

3. **Error handling**
   - If inspection fails (e.g. element not found), dialog opens with `inspection=None` and behaves as before (selector only, no pre-filled dropdowns).

**Deliverables**: End-to-end flow from click → inspection → dialog with dropdowns; optional duplicate-column warning.

**Estimated effort**: Small (0.5–1 day).

---

### Phase 4d: Polish and Edge Cases

**Objective**: Improve robustness, UX, and accessibility.

**Tasks**:

1. **Long attribute values**
   - Truncate in dropdown labels (e.g. 40–60 chars); add tooltip with full value where possible (Tk has limited tooltip support; use a status line or “View full” if needed).

2. **Duplicate column name warning**
   - When user selects or types a column name that already exists in the profile, show a warning (e.g. “This column name is already used”) and allow override or change.

3. **Keyboard and focus**
   - Ensure Enter confirms and Escape cancels; set initial focus to column name or first editable field.

4. **Documentation**
   - Update user-facing docs (e.g. INSTALL.md or a short “Using the Picker” section) to describe that selecting an element now shows its details and attribute dropdown.
   - Keep this document (`picker-enhancement.md`) in sync with implementation (e.g. add “Implemented” notes per phase).

**Deliverables**: Polish for long values, duplicate warning, keyboard behaviour, doc updates.

**Estimated effort**: Small (0.5–1 day).

---

## 5. Summary Table

| Phase | Focus | Key deliverable |
|-------|--------|------------------|
| **4a** | Element inspection in browser | JS inspector; payload (tag, attributes, text preview); picker returns inspection with selector |
| **4b** | Dialog enhancements | Column combobox with suggestions; attribute dropdown with values; element preview |
| **4c** | Wiring and profile columns | Picker → dialog with inspection; existing columns in suggestions; duplicate handling |
| **4d** | Polish | Long-value truncation, duplicate warning, keyboard, docs |

---

## 6. Dependencies and Risks

- **Playwright**: Inspection runs inside `page.evaluate`; ensure the element reference or selector is still valid when we run the inspector (same tick or immediately after click).
- **Tkinter**: Dropdown with “attribute → value” labels may need a custom combobox or listbox if ttk.Combobox does not support rich labels; a simple approach is to store `attr_name` and show `f"{name} → {value[:40]}..."` in the dropdown.
- **Backward compatibility**: Profiles and runs that were created without inspection data must still work; dialog must handle `inspection=None`.

---

## 7. Future Enhancements (Out of Scope for This Plan)

- “Pick again” from the dialog to re-open the picker without closing the dialog.
- Multiple element selection in one go (e.g. “Add all links in this list”).
- XPath in addition to CSS selector.
- Visual highlight of the selected element in the page while the dialog is open.

These can be added in later phases once the above is in place.
