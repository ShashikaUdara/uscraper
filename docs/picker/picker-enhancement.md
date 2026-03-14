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

## 4. Picker Usability: Current Issues and Desired Flow

This section describes the main usability problems with the current picker and the intended operation flow so that the tool behaves like a proper scraping picker: **hover-to-highlight**, **click-to-inspect full hierarchy**, **configure**, and **scrape all matching elements** (not just the one clicked).

### 4.1 Current Picker Issues

- **Not user-friendly; hard to understand**  
  The biggest issue. The current flow (open browser, click element, get a selector and a small dialog) does not make it obvious what will be scraped or how the choice maps to “all similar items” on the page. Users struggle to understand which area they are targeting and what the tool will do with it.

- **Only the selected element’s details are considered**  
  The picker focuses on the single element the user clicked (its tag, attributes, text). The basic use of a scraping tool is to **scrape all information that matches the same context** — i.e. all similar elements on the page. For example, if the user selects one product card or one link in a list, the tool should be designed to **pick all product cards or all links of that kind**, not just the one clicked. The current design does not make this “select one, scrape all matching” model clear, and the UI does not emphasise that the chosen selector will be used to find **all** matching elements when scraping.

- **No visual feedback before click**  
  There is no hover highlight. The user cannot see which block or area the cursor is over until after they click, which makes precise selection difficult and increases mistakes.

- **Limited hierarchy and context after click**  
  After a click, the user sees a summary (tag, attributes, text preview) and a selector. They do not see the **full element hierarchy** (parent/child chain, surrounding structure, all HTML elements and their attributes/classes/ids) in a clear, explorable way. That makes it hard to understand the page structure and to choose the right “context” (e.g. the repeating container) for scraping all similar blocks.

### 4.2 Desired Operation Flow

The operation flow should be as follows.

#### Step 1: Hover — Highlight the element under the cursor

- When the user **hovers** over the picker browser window, the element currently under the mouse should be **visually highlighted** (e.g. outline, background tint, or overlay).
- This highlight must **clearly show which area** the cursor is on, so the user can see exactly what they are about to select before clicking.
- Implementation implies injecting a script that tracks `mouseover` / `mousemove`, resolves the element under the cursor, and applies a highlight style (and removes it when the cursor leaves or moves to another element).

#### Step 2: Click — Extract the clicked block and show full element hierarchy

- When the user **clicks** that area, the **clicked block** (the target element) should be “extracted” and presented in the picker UI.
- The picker should show the **full element hierarchy** for that block, including:
  - **All HTML elements** in the path (from root to the clicked element, and optionally children).
  - **Attributes** for each node: class names, ids, data attributes, and other available attributes.
  - Any other **available details** (tag name, role, text snippet) so the user can easily understand the structure.
- This hierarchy view should be **easy to read and navigate** (e.g. tree or indented list), so the user can see the context (e.g. “this link is inside this div, inside this section”) and decide which level to use as the “repeating unit” for scraping.

#### Step 3: Configure essential elements

- Using the hierarchy and details, the user **configures the essential elements** they want to scrape (e.g. “for each card, get title, link, and price”).
- The UI should make it clear that the **selector** (or chosen level) will be used to find **all similar areas** on the page when scraping — i.e. “all elements matching this context.”

#### Step 4: Scrape — All matching areas

- When the user proceeds to **scraping**, the system must **scrape all information for the given context** — i.e. **all similar areas** on the page.
- For each configured element (e.g. “title”, “link”), the engine should use the selector to find **every matching element** on the page and extract the requested data (text, attribute, html), producing one row per repeated block (or one value per match, depending on the chosen data model).
- This is the core expectation: **select one representative block in the picker → scrape all blocks that match that context.**

### 4.3 Summary Table

| Current problem | Desired behaviour |
|-----------------|-------------------|
| No feedback before click | Hover highlights the element under the cursor so the user sees the target area. |
| Only clicked element’s details | Click opens a view showing the **full hierarchy** (elements, attributes, classes, ids) for the clicked block. |
| Unclear what gets scraped | Make explicit that the chosen selector/context is used to find **all similar elements** on the page. |
| Scrape = one element? | Scrape = **all** elements matching the configured context (all similar cards, all similar links, etc.). |

Implementing hover highlight, full-hierarchy display, and clear “scrape all matching” behaviour will require changes to both the picker (browser injection, hierarchy extraction, UI) and the documentation so users understand the flow.

---

## 5. Implementation Plan

The work is split into **phases** so that each deliverable is testable and can be merged incrementally. Phases **4a–4d** cover element inspection, dialog enhancements, wiring, and polish (several are already implemented). Phases **5a–5d** implement the picker usability and scrape-all-matching flow from **Section 4**: hover highlight, full element hierarchy on click, UI clarity that the selector matches all similar elements, and verification of the scraping logic.

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

**Progress (Phase 4a — Implemented)**:
- **Payload contract**: `ElementInspection` dataclass in `src/uscraper/engine/inspect.py` with `tag_name`, `attributes` (list of `{name, value}`), `inner_text_preview`, `html_preview`, `selector`. `from_browser_dict()` normalizes the browser object and truncates previews (80 / 200 chars).
- **JS inspector**: `get_element_inspection_js()` defines `window.__getInspection(el)`; returns `{ selector, tagName, attributes, innerTextPreview, htmlPreview }`. Injected after the selector script in the picker.
- **Picker integration**: Click handler builds the full payload in the page via `__getInspection(el)` and sends it to `__pickerCallback(payload)`. Callback accepts either a dict (inspection) or a string (selector only); queue stores `(selector, inspection)`. `get_next_selector()` now returns `(selector, inspection)` or `PICKER_CLOSED` or `None`.
- **GUI**: Main window unpacks `(selector, inspection)` and calls `ask_element_options(parent, selector, inspection)`. Dialog API accepts `inspection=None` (used in Phase 4b for dropdowns).
- **Tests**: `tests/test_inspect.py` (payload parsing, truncation, invalid input); `tests/test_picker.py` (callback with dict returns tuple, plain string returns selector + None; integration test runs inspection JS in browser and checks payload shape).

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

**Progress (Phase 4b — Implemented)**:
- **Dialog API**: `ask_element_options(parent, selector, inspection=None, existing_columns=None)`. Backward compatible when `inspection` is None.
- **Column name**: Combobox (dropdown + free text). `_column_suggestions(inspection, existing_columns)` builds options: for `<a href>` → "link"; for `<img>` → "image_src" / "image_alt"; generic tag+attr → e.g. "span_class"; always "inner_text", "html"; plus existing profile column names. Default is first suggestion.
- **Extract type**: Combo text / attribute / html. `_suggest_extract_and_attr(inspection)` suggests "attribute" + "href" for `<a>`, "attribute" + "src" for `<img>`. Attribute row is shown only when extract type is "attribute" (trace on type_var toggles visibility).
- **Attribute dropdown**: When extract type is "attribute" and inspection has attributes, readonly combobox with display `attr_name → truncated(value)` (40 chars); stored value is attr name via `attr_combo.current()`. Pre-select href for `<a>`, src for `<img>`, else first. When no attributes, "No attributes" label + Entry for manual attr name.
- **Element preview**: When inspection is present, "Element preview" section with tag, id/class if present, and inner text preview (read-only).
- **Selector**: Full selector shown (truncated in label); "Copy" button copies selector to clipboard.
- **Existing columns**: Main window passes `existing_columns` from `list_profile_elements(..., profile_id)` (column_name list) into the dialog; merged into column suggestions.
- **Tests**: `tests/test_dialogs.py` — unit tests for `_column_suggestions` and `_suggest_extract_and_attr` (a/href, img/src/alt, generic tag+attr, no inspection, existing columns).

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

**Progress (Phase 4c — Implemented)**:
- **Picker → dialog wiring**: Already in place from 4a/4b. Picker sends `(selector, inspection)`; GUI unpacks and calls `ask_element_options(parent, selector, inspection=inspection, existing_columns=existing_columns)`.
- **Existing columns**: Main window builds `existing_columns` from `list_profile_elements(conn, profile_id)` (column_name list) and passes it into the dialog. Dialog uses it in `_column_suggestions` and for duplicate check.
- **Duplicate-column warning**: In the dialog, on OK: if the chosen column name is in `existing_columns`, `messagebox.askyesno("Duplicate column name", "This column name is already used in this profile. Use it anyway?")` is shown. If the user chooses No, the dialog stays open; if Yes, the result is returned. If the user confirms and the DB still rejects (e.g. race), main window catches `sqlite3.IntegrityError` from `add_to_profile` and shows "This column name already exists in the profile. Choose a different name."
- **Error handling**: When inspection is missing or invalid, picker already passes `(selector, None)`; dialog opens with `inspection=None` and works with selector-only (no pre-filled dropdowns).
- **Tests**: `test_add_element_duplicate_column_name_raises` in `tests/test_db.py` documents that duplicate (profile_id, column_name) raises `IntegrityError` (so the GUI can catch it).

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

**Progress (Phase 4d — Implemented)**:
- **Long attribute values**: Attribute dropdown already truncates values to 40 chars (ATTR_DISPLAY_VALUE_LEN). Added a **View full** button next to the attribute dropdown; when clicked, shows the full value of the currently selected attribute in a messagebox (capped at 2000 chars for very long values).
- **Duplicate column name warning**: Implemented in Phase 4c; no change in 4d.
- **Keyboard and focus**: In the element-options dialog, **Enter** confirms (binds to OK) and **Escape** cancels. Initial focus is set to the column-name combobox via `d.after(10, col_combo.focus_set)` so the user can type or pick immediately.
- **Documentation**: Added a **Using the Picker** section to `docs/INSTALL.md` describing: profile/URL/browser, opening the picker, clicking an element, the dialog (element preview, selector with Copy, column name suggestions, Extract type, attribute dropdown with View full), OK/Cancel, and that Enter confirms and Escape cancels. This document updated with Phase 4d progress.

---

### Phase 5a: Hover highlight in the picker

**Objective**: When the user hovers over the picker browser window, the element under the cursor is visually highlighted so the user sees exactly which area they are about to select before clicking.

**Tasks**:

1. **Inject hover script in the picker**
   - On picker load (after existing init scripts), inject JavaScript that listens for `mouseover` / `mousemove` on `document` (or a suitable container).
   - Resolve the element under the cursor (e.g. `document.elementFromPoint(x, y)` or the event target).
   - Apply a **highlight style** to that element: e.g. outline (e.g. `outline: 2px solid blue`), semi-transparent background, or a dedicated overlay div. Ensure the highlight is clearly visible and does not shift layout (prefer outline or box-shadow).
   - On `mouseout` or when the cursor moves to another element, remove the highlight from the previous element and apply it to the new one. Use a single “current highlighted” reference to avoid leaving stale highlights.

2. **Performance and edge cases**
   - Throttle or debounce `mousemove` if needed so highlight updates are smooth but not janky.
   - Avoid highlighting the injected overlay/UI if any; restrict to the page’s own DOM.
   - Ensure highlight is removed when the picker closes or the page navigates.

3. **Optional: highlight the “repeating container”**
   - Later enhancement: when hovering, optionally show a secondary hint (e.g. dimmed outline) for a suggested “repeating block” (e.g. parent with many similar siblings). Can be Phase 5b or a later iteration.

**Deliverables**: Picker page shows a clear, stable highlight on the element under the cursor; no stray highlights on close/navigate.

**Estimated effort**: Small–medium (1–2 days).

---

### Phase 5b: Full element hierarchy on click

**Objective**: When the user clicks an element in the picker, extract the clicked block and show its **full element hierarchy** in the picker UI (path from root to target, all HTML elements, attributes, class names, ids, and other details) so the user can understand the structure and choose the right context for “scrape all matching.”

**Tasks**:

1. **Hierarchy payload (browser)**
   - Extend the inspection script (or add a new one) that, given the clicked element, returns a **hierarchy** structure, e.g.:
     - **Path from root**: list of nodes from `document.documentElement` (or `body`) down to the clicked element. For each node: `tagName`, `id`, `classList` or `className`, `attributes` (name → value), optional short `textPreview` or `innerText` snippet.
     - **Clicked node**: full details (tag, id, classes, all attributes, inner text preview, outer HTML snippet).
     - **Optional**: first level of children of the clicked element (tag + key attributes) so the user sees what’s inside the block.
   - Serialize to a JSON-friendly structure (no circular refs); cap text/HTML length per node to keep payload size reasonable.

2. **GUI: hierarchy view**
   - After a click, show the hierarchy in the picker UI (main window or a dedicated panel/dialog). Display as an **expandable tree** or **indented list**: each level shows tag name, id, class(es), and key attributes. User can expand/collapse to see the path from root to the clicked element and optionally its children.
   - Use the existing **selector** (and inspection) to drive the “configure element” flow: e.g. “Add this element” or “Use this level” so the user can add the current node (or a chosen ancestor) as a scrape element. The existing element-options dialog can still be used for column name, extract type, and attribute.

3. **Integration with existing flow**
   - Keep current behaviour: click → selector + inspection → element-options dialog. Add the hierarchy view as an **additional** panel or step (e.g. show hierarchy first, then “Configure” opens the element-options dialog with the same selector/inspection). Alternatively: show hierarchy and element-options in one screen (hierarchy on one side, form on the other).

**Deliverables**: Click in picker produces a full hierarchy (path + clicked node + optional children); GUI shows this in a tree or indented list; user can proceed to configure the element and add it to the profile.

**Estimated effort**: Medium (2–3 days).

---

### Phase 5c: UI clarity — “Scrape all matching elements”

**Objective**: Make it explicit in the UI that the chosen selector will be used to find **all similar elements** on the page when scraping (select one representative → scrape all matching), so users understand the tool’s behaviour.

**Tasks**:

1. **In the element-options dialog (or hierarchy view)**
   - Add a short, visible line of copy, e.g.: “When you run a scrape, the tool will find **all elements** on the page that match this selector and extract the chosen field for each.”
   - Optionally show a **live count** in the picker: after the user has chosen a selector, run `document.querySelectorAll(selector).length` in the page and display “This selector matches **N** elements on the current page.” (Update when they change selector or when they add another element.)

2. **In the main window and run flow**
   - In the “Run scrape” area or status text, optionally remind: “Scraping will extract data for **all** elements matching each configured selector.”
   - In `docs/INSTALL.md` and `docs/picker/scraping-flow.md`, state clearly that one configured element (e.g. “link”) results in one column in the CSV with **one value per matching element** (rows aligned by max count across columns).

3. **Optional: preview in picker**
   - When the user has added one or more elements, show a small “Preview” that lists selectors and, for each, the current match count on the page. Helps users spot typos or overly narrow/wide selectors.

**Deliverables**: Clear in-app and doc wording that scraping uses “all matching elements”; optional match count and short reminder in run flow.

**Estimated effort**: Small (0.5–1 day).

---

### Phase 5d: Scraping logic — all matching elements (verify and document)

**Objective**: Ensure the scraping engine **already** extracts data for **all** elements matching each selector (not just the first), and document this behaviour; fix or extend if needed.

**Tasks**:

1. **Verify current behaviour**
   - In `run_scrape`, for each scrape element the engine uses `page.locator(selector)` and iterates over **all** matches (e.g. `locator.count()` and `locator.nth(i)` for text/attribute/html). Confirm that this yields one value per matching element and that rows are built by aligning columns (max length, pad with ""). No change if behaviour is correct.

2. **Fix if needed**
   - If any code path only takes the first match (e.g. `locator.first` only), change it to iterate all matches so that “scrape all matching” is guaranteed for every column.

3. **Document**
   - In `docs/picker/scraping-flow.md` (and this document), state explicitly: “For each configured element, the engine finds **all** DOM nodes matching the selector and extracts the requested field (text, attribute, or html). The CSV has one row per index; if column A has 10 matches and column B has 8, the last 2 rows for column B are padded with empty string.”
   - Add a one-line comment in the runner (e.g. above `_extract_column_values` or `_extract_all_elements`) that says we extract **all** matches for each selector.

**Deliverables**: Confirmation (or fix) that scraping uses all matches per selector; short doc and code comment describing “scrape all matching.”

**Estimated effort**: Small (0.5 day).

---

## 6. Summary Table

| Phase | Focus | Key deliverable | Status |
|-------|--------|------------------|--------|
| **4a** | Element inspection in browser | JS inspector; payload (tag, attributes, text preview); picker returns inspection with selector | **Done** |
| **4b** | Dialog enhancements | Column combobox with suggestions; attribute dropdown with values; element preview | **Done** |
| **4c** | Wiring and profile columns | Picker → dialog with inspection; existing columns in suggestions; duplicate handling | **Done** |
| **4d** | Polish | Long-value truncation, duplicate warning, keyboard, docs | **Done** |
| **5a** | Hover highlight | Picker highlights element under cursor on hover (outline/overlay) | Pending |
| **5b** | Full element hierarchy | On click, extract and show full DOM hierarchy (path + node + optional children) in GUI | Pending |
| **5c** | UI clarity | In-app and docs: “scrape all matching elements” and optional match count | Pending |
| **5d** | Scraping logic | Verify/fix “all matches” per selector; document and comment in code | Pending |

---

## 7. Dependencies and Risks

- **Playwright**: Inspection runs inside `page.evaluate`; ensure the element reference or selector is still valid when we run the inspector (same tick or immediately after click).
- **Tkinter**: Dropdown with “attribute → value” labels may need a custom combobox or listbox if ttk.Combobox does not support rich labels; a simple approach is to store `attr_name` and show `f"{name} → {value[:40]}..."` in the dropdown.
- **Backward compatibility**: Profiles and runs that were created without inspection data must still work; dialog must handle `inspection=None`.

---

## 8. Future Enhancements (Out of Scope for Current Phases)

- “Pick again” from the dialog to re-open the picker without closing the dialog.
- Multiple element selection in one go (e.g. “Add all links in this list”).
- XPath in addition to CSS selector.
- **Suggested repeating container**: when hovering (Phase 5a), optionally infer and highlight a parent that looks like a repeating block (e.g. list item wrapper) to help users pick the right scope for "scrape all matching."

Note: **Hover highlight** and **full element hierarchy** are now in the implementation plan as Phase 5a and Phase 5b.
