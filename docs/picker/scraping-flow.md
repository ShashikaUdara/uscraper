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
