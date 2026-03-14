# Web Scraping Flow and Application Behaviour

This document explains how web scraping works in general, how the uscraper application works today, and a list of current issues and limitations.

---

## 1. How Web Scraping Works

Web scraping is the process of programmatically visiting web pages, locating specific parts of the document (elements), and extracting data from them.

### 1.1 High-level steps

1. **Fetch the page**  
   A browser or HTTP client loads a URL. The server returns HTML (and often CSS/JS). For dynamic sites, a real browser (or headless browser) runs JavaScript so the final DOM reflects what the user would see.

2. **Parse the document**  
   The HTML is parsed into a tree structure (the DOM — Document Object Model). The DOM is the in-memory representation of the page structure (tags, attributes, text nodes).

3. **Locate elements**  
   Elements are identified using **selectors**. Common approaches:
   - **CSS selectors**: e.g. `a.link`, `#main`, `div > ul li:nth-child(2)` — match by tag, id, class, hierarchy, position.
   - **XPath**: path-based expressions (e.g. `/html/body/div[1]/a`).
   - Our app uses **CSS selectors** only.

4. **Extract data**  
   For each matched element, we read:
   - **Text**: visible text content (`innerText` / `textContent`).
   - **Attributes**: e.g. `href`, `src`, `data-*`.
   - **HTML**: raw markup of the element (`innerHTML` / `outerHTML`).

5. **Structure and export**  
   Extracted values are arranged into rows and columns (e.g. one row per list item, one column per chosen field) and written to a file (CSV, JSON, etc.) or database.

### 1.2 Why use a real browser?

- **JavaScript-rendered content**: Many sites build their content with JS. A simple HTTP request only gets the initial HTML; a browser runs scripts and produces the final DOM.
- **Cookies, sessions, redirects**: A browser handles login, cookies, and redirects like a normal user.
- **Interactions**: Clicks, scrolls, and form submissions can be automated to reach the right state before scraping.

Our application uses **Playwright** to drive a real browser (Chromium, Firefox, or WebKit), so we can scrape pages that depend on JavaScript.

---

## 2. How Our Application Works at the Moment

### 2.1 Data model

- **Profiles**: Each scrape is defined by a **profile** — a name, a **single URL**, a chosen browser, and optional Playwright options (e.g. `timeout`, `viewport`, `headless`).
- **Elements**: For each profile we define **scrape elements**: a CSS **selector**, an **extract type** (text, attribute, or html), and an optional **attribute name** (for `extract_type=attribute`). Each element has a **column name** used in the output CSV.
- **Runs**: Each time we run a profile we create a **run** record (start time, status, output path, row count, error message). Scraped data is **not** stored in the DB; it is written only to CSV.

### 2.2 Defining what to scrape (element picker)

1. User selects or creates a profile and enters the URL.
2. User selects an installed browser and clicks **Select elements**.
3. A browser window opens at that URL. The app injects scripts that:
   - Generate a **stable CSS selector** for the clicked element (using `id` if unique, otherwise a path of `tag:nth-child(n)` from the root).
   - Collect **inspection data**: tag name, attributes, and a short text preview.
4. Each click sends the **selector** and **inspection** back to the app. The **element options** dialog opens with:
   - Element preview and selector (with Copy).
   - Suggested **column name** (e.g. "link" for `<a href>`, "image_src" for `<img src>`).
   - **Extract type**: text, attribute, or html; if attribute, a dropdown of the element’s attributes (name → value) and a "View full" for long values.
   - Optional duplicate-column warning and existing profile columns in suggestions.
5. User confirms (OK) or cancels. On OK, the element is appended to the profile’s scrape elements (selector, column name, extract type, extract arg). The picker stays open so more elements can be added; closing the browser ends the picker.

### 2.3 Running a scrape

1. User clicks **Run scrape** for the current profile.
2. **run_scrape(profile_id)**:
   - Loads the profile (URL, browser_id, options) and its scrape elements from the DB.
   - Resolves the browser’s driver (must be installed; we use Playwright with a marker like `playwright:chromium`).
   - Builds the output path: `{output_dir}/scrape_{profile_name}_{timestamp}.csv` (output_dir from app config).
   - Inserts a **run** row with status `running` and the CSV path.
   - Launches the browser (headless by default from options), opens a single page, and calls **page.goto(profile["url"], wait_until="domcontentloaded", timeout=...)**.
   - For each scrape element, **page.locator(selector)** is used; for each match we extract text, an attribute, or HTML according to `extract_type` and `extract_arg`.
   - Columns are aligned by **maximum number of matches** across all selectors; shorter columns are padded with empty strings so the result is a rectangular table.
   - Writes the table to CSV (UTF-8, header = column names) and updates the run with status `completed` and row count. On any exception, the run is updated with status `failed` and the error message.

3. The GUI runs this in a background thread and shows status; on completion it shows the output path and row count or an error.

### 2.4 Output

- One **CSV file per run**, in the configured output directory.
- Filename: `scrape_{profile_name}_{YYYY-MM-DD_HH-MM-SS}.csv`.
- No scraped data is stored in the application database; only run metadata (path, status, row count, error) is kept.

### 2.5 Technical summary

| Aspect | Implementation |
|--------|----------------|
| Browser | Playwright (sync API); Chromium, Firefox, or WebKit |
| Page load | Single `goto`; wait until `domcontentloaded` (no `networkidle`) |
| Selectors | CSS only (id or tag:nth-child path from picker) |
| Extract types | text, attribute, html |
| Data alignment | Rows = max number of matches across columns; pad with "" |
| Output | One CSV per run; UTF-8; path and run metadata in DB |

---

## 3. Issues and Limitations

The following list describes current limitations and known issues of the application. Each item is a short description to guide future improvements.

---

### 3.1 Single URL and single page

- **Single URL per profile**: A profile has exactly one URL. There is no support for multiple URLs per profile (e.g. a list of product pages) or for following links from the page.
- **Single page load**: Each run does one `goto`. There is no built-in pagination (e.g. “Next” button), no multi-step flows (e.g. search then results), and no crawling.

*Impact*: Users must create separate profiles or manually manage many URLs; paginated or multi-step sites need custom handling outside the app.

---

### 3.2 No authentication or session handling

- **No login flow**: The app does not support logging in (forms, cookies, or session storage). Pages that require authentication will not be scrapable unless the user manually obtains a session (e.g. cookies) and there is no way to inject that into the app today.
- **No cookie/header configuration**: Users cannot set custom cookies, headers, or bearer tokens for the request.

*Impact*: Only public, non-login-required pages are supported in practice.

---

### 3.3 Selector fragility

- **Selector strategy**: The picker generates selectors using `id` (if unique) or a path of `tag:nth-child(n)`. These can break when:
  - The site’s structure or order of elements changes (e.g. new sidebar, reordered list).
  - Dynamic IDs or generated class names change between visits.
- **No XPath**: Only CSS selectors are supported; some targets are easier or more stable with XPath.
- **No fallback or retry**: If a selector matches zero elements, that column is filled with empty strings; there is no fallback selector or retry logic.

*Impact*: Scrapes can silently return empty columns or wrong data when the page structure changes.

---

### 3.4 Timing and dynamic content

- **Load strategy**: We wait only for `domcontentloaded`. Content that appears later (e.g. after more JavaScript or after a delay) may not be present when we extract.
- **No explicit wait for elements**: There is no “wait for selector” or “wait for network” before extraction. If the content of interest loads slowly or after an API call, it may be missing.
- **No configurable delay**: Users cannot add a fixed delay (e.g. 2 seconds) after load before scraping.

*Impact*: Heavily dynamic or slow-loading pages may yield incomplete or empty data.

---

### 3.5 Extraction capabilities

- **Only three extract types**: text, attribute, html. There is no support for:
  - Multiple attributes per element (e.g. both `href` and `title` in one row).
  - Regex or substring extraction from text/attributes.
  - Nested or parent/child extraction in one step.
- **Row alignment**: Rows are built by “max count” across columns and padding with `""`. If selectors match different logical items (e.g. titles from one list and links from another with different lengths), rows can be misaligned and not reflect true record boundaries.

*Impact*: Some extraction patterns require multiple elements or post-processing outside the app.

---

### 3.6 Error handling and robustness

- **No retries**: A single failure (timeout, network, selector match zero) fails the run; there is no automatic retry with backoff.
- **Timeout handling**: Only a global goto timeout (and optional profile `timeout` in options) exists. Long-running or flaky pages can consistently fail without finer control.
- **Partial failure**: If extraction fails mid-way (e.g. one selector throws), the whole run fails; there is no “best effort” partial CSV.

*Impact*: Temporary network or site issues require the user to re-run manually; no resilience for unstable targets.

---

### 3.7 Concurrency and scheduling

- **One run at a time from GUI**: The “Run scrape” action starts a single run in a background thread. There is no queue, no “run all profiles,” and no scheduling (cron-like or in-app).
- **No rate limiting**: The app does not throttle requests or add delays between runs, which can be important for polite scraping.

*Impact*: Bulk or scheduled scraping is not supported; users must trigger runs manually or script externally.

---

### 3.8 Platform and deployment

- **Linux-focused**: Implementation and packaging (e.g. Makefile, install docs) target Linux (Ubuntu). The stack (Python, Tkinter, Playwright) can run elsewhere, but there is no documented or tested flow for Windows/macOS.
- **Single user / single machine**: Configuration and DB live under `~/.config/uscraper/`. There is no multi-user or server mode; no API for remote control or integration with other tools.

*Impact*: Suited for a single desktop user on Linux; not designed for shared or headless server use out of the box.

---

### 3.9 Picker and GUI

- **Picker must run on main thread**: Playwright’s sync API is used from the main GUI thread for the picker (to avoid greenlet/thread issues). Opening the picker blocks briefly while the browser starts.
- **No in-app preview of CSV**: After a run, the user is told the path and row count but cannot open or preview the CSV inside the app.
- **No run history per profile in GUI**: Run metadata exists in the DB (`scrape_runs`) but the GUI does not list past runs or their status/output path for the current profile.

*Impact*: Some workflows (e.g. inspect last run’s output, re-run failed) require using the file manager or DB directly.

---

### 3.10 Configuration and profile options

- **Limited profile options**: `options_json` can pass `headless`, `timeout`, `viewport` to Playwright. There is no UI to edit these; they would need to be set in the DB or via a future “advanced options” screen.
- **No environment or proxy**: No support for HTTP/HTTPS proxy or environment-specific config (e.g. different output dir per environment).

*Impact*: Power users cannot easily tune browser or network behaviour without touching the DB or code.

---

This list can be used to prioritise improvements (e.g. pagination, auth, selector robustness, retries, scheduling) and to set expectations for what the application supports today.

---

## 4. Picker Usability: Current Issues and Desired Flow

This section describes the main usability problems with the current picker and the intended operation flow so that the tool behaves like a proper scraping picker: **hover-to-highlight**, **click-to-inspect full hierarchy**, **configure**, and **scrape all matching elements** (not just the one clicked).

### 4.1 Current Picker Issues

- **Not user-friendly; hard to understand**  
  The biggest issue. The current flow (open browser, click element, get a selector and a small dialog) does not make it obvious what will be scraped or how the choice maps to "all similar items" on the page. Users struggle to understand which area they are targeting and what the tool will do with it.

- **Only the selected element's details are considered**  
  The picker focuses on the single element the user clicked (its tag, attributes, text). The basic use of a scraping tool is to **scrape all information that matches the same context** — i.e. all similar elements on the page. For example, if the user selects one product card or one link in a list, the tool should be designed to **pick all product cards or all links of that kind**, not just the one clicked. The current design does not make this "select one, scrape all matching" model clear, and the UI does not emphasise that the chosen selector will be used to find **all** matching elements when scraping.

- **No visual feedback before click**  
  There is no hover highlight. The user cannot see which block or area the cursor is over until after they click, which makes precise selection difficult and increases mistakes.

- **Limited hierarchy and context after click**  
  After a click, the user sees a summary (tag, attributes, text preview) and a selector. They do not see the **full element hierarchy** (parent/child chain, surrounding structure, all HTML elements and their attributes/classes/ids) in a clear, explorable way. That makes it hard to understand the page structure and to choose the right "context" (e.g. the repeating container) for scraping all similar blocks.

### 4.2 Desired Operation Flow

The operation flow should be as follows.

#### Step 1: Hover — Highlight the element under the cursor

- When the user **hovers** over the picker browser window, the element currently under the mouse should be **visually highlighted** (e.g. outline, background tint, or overlay).
- This highlight must **clearly show which area** the cursor is on, so the user can see exactly what they are about to select before clicking.
- Implementation implies injecting a script that tracks `mouseover` / `mousemove`, resolves the element under the cursor, and applies a highlight style (and removes it when the cursor leaves or moves to another element).

#### Step 2: Click — Extract the clicked block and show full element hierarchy

- When the user **clicks** that area, the **clicked block** (the target element) should be "extracted" and presented in the picker UI.
- The picker should show the **full element hierarchy** for that block, including:
  - **All HTML elements** in the path (from root to the clicked element, and optionally children).
  - **Attributes** for each node: class names, ids, data attributes, and other available attributes.
  - Any other **available details** (tag name, role, text snippet) so the user can easily understand the structure.
- This hierarchy view should be **easy to read and navigate** (e.g. tree or indented list), so the user can see the context (e.g. "this link is inside this div, inside this section") and decide which level to use as the "repeating unit" for scraping.

#### Step 3: Configure essential elements

- Using the hierarchy and details, the user **configures the essential elements** they want to scrape (e.g. "for each card, get title, link, and price").
- The UI should make it clear that the **selector** (or chosen level) will be used to find **all similar areas** on the page when scraping — i.e. "all elements matching this context."

#### Step 4: Scrape — All matching areas

- When the user proceeds to **scraping**, the system must **scrape all information for the given context** — i.e. **all similar areas** on the page.
- For each configured element (e.g. "title", "link"), the engine should use the selector to find **every matching element** on the page and extract the requested data (text, attribute, html), producing one row per repeated block (or one value per match, depending on the chosen data model).
- This is the core expectation: **select one representative block in the picker → scrape all blocks that match that context.**

### 4.3 Summary Table

| Current problem | Desired behaviour |
|-----------------|-------------------|
| No feedback before click | Hover highlights the element under the cursor so the user sees the target area. |
| Only clicked element's details | Click opens a view showing the **full hierarchy** (elements, attributes, classes, ids) for the clicked block. |
| Unclear what gets scraped | Make explicit that the chosen selector/context is used to find **all similar elements** on the page. |
| Scrape = one element? | Scrape = **all** elements matching the configured context (all similar cards, all similar links, etc.). |

Implementing hover highlight, full-hierarchy display, and clear "scrape all matching" behaviour will require changes to both the picker (browser injection, hierarchy extraction, UI) and the documentation so users understand the flow.

---

## 5. Implementation Plan

The work is split into **phases** so that each deliverable is testable and can be merged incrementally. Phases **4a–4d** cover element inspection, dialog enhancements, wiring, and polish (several are already implemented). Phases **5a–5d** implement the picker usability and scrape-all-matching flow from **Section 4**: hover highlight, full element hierarchy on click, UI clarity that the selector matches all similar elements, and verification of the scraping logic.

### Phase 4a: Element Inspection (Data Collection in Browser)

**Objective**: From the picker, when the user clicks an element, collect a structured payload (tag, attributes, text preview, selector) in the browser and pass it to the application.

**Tasks**: (1) Define inspection payload (contract): `tagName`, `attributes` (list of `{name, value}`), `innerTextPreview` (max 80), `htmlPreview` (max 200), `selector`. (2) Implement JS snippet in `engine/inspect.py`: `get_element_inspection_js()` defining `window.__getInspection(el)`. (3) Integrate into picker flow: click handler runs inspector and sends payload. (4) Pass inspection result to GUI; backward compatibility when inspection is missing.

**Deliverables**: Inspection payload type, JS inspector, picker returns inspection with selector, tests.

**Progress (Phase 4a — Implemented)**  
- **Payload**: `ElementInspection` dataclass in `src/uscraper/engine/inspect.py` (`tag_name`, `attributes`, `inner_text_preview`, `html_preview`, `selector`); `from_browser_dict()` normalises browser payload and truncates previews (80 / 200 chars).  
- **JS inspector**: `get_element_inspection_js()` defines `window.__getInspection(el)`; returns `{ selector, tagName, attributes, innerTextPreview, htmlPreview }`. Injected after the selector script in the picker.  
- **Picker**: Click handler builds payload via `__getInspection(el)` and sends to `__pickerCallback(payload)`; callback accepts dict or string (backward compat); `get_next_selector()` returns `(selector, inspection)` or `PICKER_CLOSED` or `None`.  
- **GUI**: Main window unpacks `(selector, inspection)` and calls `ask_element_options(parent, selector, inspection)`.  
- **Verify**: `pytest tests/test_inspect.py tests/test_picker.py` — all tests pass.

### Phase 4b: Element Options Dialog – Pre-fill and Attribute Dropdown

**Objective**: Dialog accepts inspection and shows dropdowns with the element's real attributes and values.

**Tasks**: Dialog API with `inspection=None`, `existing_columns=None`; column name combobox with suggestions; extract type (text/attribute/html); attribute dropdown with `attr_name → value`; element preview; selector with Copy.

**Progress (Phase 4b — Implemented)**  
- **Dialog API**: `ask_element_options(parent, selector, inspection=None, existing_columns=None)` in `src/uscraper/gui/dialogs.py`. Backward compatible when `inspection` is None.  
- **Column name**: Combobox (dropdown + free text). `_column_suggestions(inspection, existing_columns)` builds options: e.g. "link" for `<a href>`, "image_src"/"image_alt" for `<img>`, generic `tag_attr`; always "inner_text", "html"; plus existing profile column names. Default is first suggestion.  
- **Extract type**: Combo text / attribute / html. `_suggest_extract_and_attr(inspection)` suggests "attribute" + "href" for `<a>`, "attribute" + "src" for `<img>`. Attribute row shown only when extract type is "attribute".  
- **Attribute dropdown**: When extract type is "attribute" and inspection has attributes, readonly combobox with display `attr_name → truncated(value)` (40 chars); stored value is attr name. Pre-select href for `<a>`, src for `<img>`, else first. "View full" button shows full value in a messagebox. When no attributes, "No attributes" label + Entry for manual attr name.  
- **Element preview**: When inspection is present, "Element preview" section with tag, id/class if present, and inner text preview (read-only).  
- **Selector**: Full selector shown (truncated in label); "Copy" button copies selector to clipboard.  
- **Verify**: `pytest tests/test_dialogs.py` — all tests pass (column suggestions, extract/attr suggestions, with/without inspection and existing columns).

### Phase 4c: Picker–Dialog Wiring and Profile Column List

**Objective**: Wire picker to dialog with inspection and existing columns; duplicate-column warning.

**Progress (Phase 4c — Implemented)**  
- **Picker → dialog wiring**: In `gui/main_window.py`, `_on_picker_selector(selector, inspection)` receives `(selector, inspection)` from the picker and calls `ask_element_options(self.root, selector, inspection, existing_columns)`. Flow is already in place from Phase 4a/4b.  
- **Existing columns**: When a profile is selected (`_current_profile_id`), main window builds `existing_columns` from `list_profile_elements(conn, profile_id)` (column_name for each element) and passes it into the dialog. Dialog uses it in `_column_suggestions` and for the duplicate check.  
- **Duplicate-column warning (dialog)**: In the element-options dialog, on OK: if the chosen column name is in `existing_columns`, `messagebox.askyesno("Duplicate column name", "This column name is already used in this profile. Use it anyway?")` is shown. If the user chooses No, the dialog stays open; if Yes, the result is returned.  
- **IntegrityError (main window)**: If the user confirms and the DB still rejects (e.g. race or override), main window catches `sqlite3.IntegrityError` from `add_to_profile` and shows "This column name already exists in the profile. Choose a different name."  
- **Verify**: `tests/test_db.py::test_add_element_duplicate_column_name_raises` documents that duplicate (profile_id, column_name) raises `IntegrityError`; picker and dialog tests pass.

### Phase 4d: Polish and Edge Cases

**Objective**: Long-value truncation, View full button, keyboard (Enter/Escape), focus, docs.

**Progress (Phase 4d — Implemented)**  
- **Long attribute values**: Attribute dropdown already truncates values to 40 chars (`ATTR_DISPLAY_VALUE_LEN` in `gui/dialogs.py`). A **View full** button next to the attribute dropdown shows the full value of the currently selected attribute in a messagebox (capped at 2000 chars for very long values).  
- **Duplicate column name warning**: Implemented in Phase 4c (dialog asks "Use it anyway?"; main window catches `IntegrityError`); no change in 4d.  
- **Keyboard and focus**: In the element-options dialog, **Enter** confirms (bound to OK) and **Escape** cancels. Initial focus is set to the column-name combobox via `d.after(10, col_combo.focus_set)` so the user can type or pick immediately.  
- **Documentation**: A **Using the Picker** section in `docs/INSTALL.md` describes: profile/URL/browser, opening the picker, clicking an element, the dialog (element preview, selector with Copy, column name suggestions, Extract type, attribute dropdown with View full), OK/Cancel, and that Enter confirms and Escape cancels.

### Phase 5a: Hover highlight in the picker

**Objective**: When the user hovers over the picker browser, the element under the cursor is visually highlighted (outline/overlay) so the user sees which area they are about to select.

**Tasks**: Inject hover script (mouseover/mousemove), resolve element under cursor, apply highlight style, remove on mouseout; throttle if needed; remove highlight on picker close/navigate.

**Deliverables**: Clear, stable highlight on hover; no stray highlights.

**Progress (Phase 5a — Implemented)**  
- **Hover script**: `get_picker_hover_highlight_js()` in `src/uscraper/engine/picker.py` injects a script that adds a `<style>` for class `.uscraper-picker-highlight` (blue outline, 2px solid, 2px offset) and listens to `mousemove` (capture) and `mouseout`. Uses `document.elementFromPoint(clientX, clientY)` to resolve the element under the cursor; applies the class to that element and removes it from the previously highlighted one. Skips `document.documentElement` and `document.body` so the whole page is not highlighted.  
- **Throttling**: Updates are throttled via `requestAnimationFrame`; last coordinates are stored so the RAF callback uses current position.  
- **Cleanup**: On `mouseout`, if `relatedTarget` is null or not in `document.body`, the highlight is removed (mouse left the window). When the picker closes or the page navigates, the DOM is torn down so no explicit cleanup is needed.  
- **Injection**: The hover script is evaluated after the click listener in `ElementPickerSession.__enter__`, so the picker window shows hover highlight as soon as it is ready.  
- **Verify**: `pytest tests/test_picker.py` — including `test_hover_highlight_js_returns_expected_content`.

### Phase 5b: Full element hierarchy on click

**Objective**: On click, extract the clicked block and show its full element hierarchy in the picker UI (path from root, all elements, attributes, classes, ids) so the user can choose the right context for "scrape all matching."

**Tasks**: Hierarchy payload (browser): path from root, clicked node details, optional children; GUI: tree or indented list; integrate with configure flow.

**Deliverables**: Full hierarchy on click; hierarchy view in GUI.

**Progress (Phase 5b — Implemented)**  
- **Hierarchy payload (browser)**: `get_element_hierarchy_js()` in `src/uscraper/engine/inspect.py` defines `window.__getHierarchy(el)`, returning `{ pathFromRoot, clickedNode, children }`. Path from root: nodes from document root down to the clicked element; each node has tagName, id, className, attributes (name/value, value truncated), textPreview (capped). clickedNode: same structure for the clicked element. children: first-level child elements (up to 20), same node shape.  
- **Python types**: `HierarchyNode` (tag_name, id, class_name, attributes, text_preview) and `ElementHierarchy` (path_from_root, clicked_node, children) with `from_browser_dict()` in `inspect.py`.  
- **Picker**: Click handler merges `payload.hierarchy = window.__getHierarchy(el)` into the payload; callback unpacks and queues `(selector, inspection, hierarchy)`. `get_next_selector()` returns that 3-tuple. Hierarchy script is evaluated after inspection script.  
- **GUI**: Main window passes `hierarchy` into `ask_element_options(..., hierarchy)`. Dialog shows an **Element hierarchy** section (when hierarchy is present): read-only scrollable Text with indented path from root, "← clicked" on the last path node, then first-level children. Node display: `<tag>#id.class`.  
- **Verify**: `pytest tests/test_inspect.py tests/test_picker.py` — hierarchy JS, HierarchyNode/ElementHierarchy parsing, picker 3-tuple return; dialog accepts hierarchy.

### Phase 5c: UI clarity — "Scrape all matching elements"

**Objective**: Make explicit in the UI that the chosen selector will be used to find **all similar elements** when scraping.

**Tasks**: Short copy in dialog (e.g. "When you run a scrape, the tool will find **all elements** that match this selector"); optional live match count; reminder in run flow; doc updates.

**Progress (Phase 5c — Implemented)**  
- **Element-options dialog**: Added a short line (Phase 5c): "When you run a scrape, the tool will find all elements on the page that match this selector and extract the chosen field for each." Shown in gray below the Selector row. When the picker sends a **match count** (number of elements matching the selector on the current page), the dialog also shows "This selector matches N element(s) on the current page." in bold.  
- **Live match count**: In the picker click handler (JS), after building the payload, `payload.matchCount = document.querySelectorAll(payload.selector || '').length` is set and sent. The GUI receives it as the 4th value from `get_next_selector()` and passes it into `ask_element_options(..., match_count)`.  
- **Main window**: A reminder label next to **Run scrape**: "(Scraping extracts data for all elements matching each selector.)" in gray.  
- **Docs**: In `docs/INSTALL.md`, added a sentence under "Using the Picker": "When you run a scrape, the tool finds **all elements** on the page that match each configured selector and extracts the chosen field … for each, producing one row per match in the CSV."

### Phase 5d: Scraping logic — all matching elements (verify and document)

**Objective**: Ensure the engine extracts data for **all** elements matching each selector; document and fix if needed.

**Tasks**: Verify `run_scrape` uses all matches (`locator.count()`, `locator.nth(i)`); document in scraping-flow.md; add code comment.

**Status**: Pending.

---

## 6. Summary Table

| Phase | Focus | Key deliverable | Status |
|-------|--------|------------------|--------|
| **4a** | Element inspection in browser | JS inspector; payload; picker returns inspection with selector | **Done** |
| **4b** | Dialog enhancements | Column combobox; attribute dropdown; element preview | **Done** |
| **4c** | Wiring and profile columns | Inspection + existing columns; duplicate handling | **Done** |
| **4d** | Polish | Long-value truncation, View full, keyboard, docs | **Done** |
| **5a** | Hover highlight | Picker highlights element under cursor on hover | **Done** |
| **5b** | Full element hierarchy | On click, show full DOM hierarchy in GUI | **Done** |
| **5c** | UI clarity | "Scrape all matching" wording and optional match count | **Done** |
| **5d** | Scraping logic | Verify/fix all matches per selector; document | Pending |

---

## 7. Dependencies and Risks

- **Playwright**: Inspection runs inside `page.evaluate`; ensure the element reference or selector is still valid when we run the inspector (same tick or immediately after click).
- **Tkinter**: Dropdown with "attribute → value" labels; store attr name and show truncated value in the dropdown.
- **Backward compatibility**: Profiles and runs created without inspection data must still work; dialog must handle `inspection=None`.

---

## 8. Future Enhancements (Out of Scope for Current Phases)

- "Pick again" from the dialog to re-open the picker without closing the dialog.
- Multiple element selection in one go (e.g. "Add all links in this list").
- XPath in addition to CSS selector.
- **Suggested repeating container**: when hovering (Phase 5a), optionally infer and highlight a parent that looks like a repeating block to help users pick the right scope for "scrape all matching."

Note: **Hover highlight** and **full element hierarchy** are in the implementation plan as Phase 5a and Phase 5b.
