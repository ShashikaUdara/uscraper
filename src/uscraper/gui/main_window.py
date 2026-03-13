"""
Main application window: profile, URL, browser, element picker, run scrape.
Uses Tkinter; long-running work (install, picker, scrape) runs in threads.
"""
import queue
import sqlite3
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, List, Dict, Any

from uscraper.config import get_config_dir
from uscraper.db import (
    ensure_db,
    list_browsers,
    list_profiles,
    get_profile,
    get_profile_with_elements,
    create_profile,
    update_profile,
    ensure_browser_installed,
    get_config,
    set_config,
    get_config_default,
)
from uscraper.engine import (
    ElementPickerSession,
    PICKER_CLOSED,
    list_profile_elements,
    remove_profile_element,
    run_scrape,
)
from uscraper.engine.runner import OUTPUT_DIR_CONFIG_KEY
from uscraper.gui.dialogs import ask_profile, ask_element_options, ask_output_dir


class MainWindow:
    def __init__(self):
        self.conn = ensure_db()
        self.root = tk.Tk()
        self.root.title("uscraper — Universal Web Scraper")
        self.root.minsize(520, 420)
        self.root.geometry("640x500")

        self._current_profile_id: Optional[int] = None
        self._picker_session: Optional[ElementPickerSession] = None
        self._picker_queue: queue.Queue = queue.Queue()
        self._after_id: Optional[str] = None
        self._picker_after_id: Optional[str] = None

        self._build_ui()
        self._refresh_browsers()  # Before _refresh_profiles so _on_profile_selected can use _browsers
        self._refresh_profiles()
        self._poll_picker_queue()

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        # --- Profile ---
        pf = ttk.LabelFrame(main, text="Profile", padding=5)
        pf.pack(fill=tk.X, pady=(0, 5))
        row0 = ttk.Frame(pf)
        row0.pack(fill=tk.X)
        ttk.Label(row0, text="Profile:").pack(side=tk.LEFT, padx=(0, 5))
        self.profile_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(
            row0, textvariable=self.profile_var, width=35, state="readonly"
        )
        self.profile_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_selected)
        ttk.Button(row0, text="New…", command=self._new_profile).pack(side=tk.LEFT, padx=2)

        ttk.Label(pf, text="URL:").pack(anchor="w")
        self.url_var = tk.StringVar(value="https://")
        self.url_entry = ttk.Entry(pf, textvariable=self.url_var, width=70)
        self.url_entry.pack(fill=tk.X, pady=2)

        # --- Browser ---
        bf = ttk.LabelFrame(main, text="Browser", padding=5)
        bf.pack(fill=tk.X, pady=(0, 5))
        brow_row = ttk.Frame(bf)
        brow_row.pack(fill=tk.X)
        ttk.Label(brow_row, text="Browser:").pack(side=tk.LEFT, padx=(0, 5))
        self.browser_var = tk.StringVar()
        self.browser_combo = ttk.Combobox(
            brow_row, textvariable=self.browser_var, width=25, state="readonly"
        )
        self.browser_combo.pack(side=tk.LEFT, padx=5)
        self.install_btn = ttk.Button(brow_row, text="Install / Use", command=self._install_browser)
        self.install_btn.pack(side=tk.LEFT, padx=5)
        self.browser_status_var = tk.StringVar(value="")
        ttk.Label(brow_row, textvariable=self.browser_status_var, foreground="gray").pack(side=tk.LEFT, padx=5)

        # --- Actions + Elements ---
        af = ttk.Frame(main)
        af.pack(fill=tk.X, pady=(0, 5))
        self.picker_btn = ttk.Button(af, text="Select elements", command=self._start_picker)
        self.picker_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.run_btn = ttk.Button(af, text="Run scrape", command=self._run_scrape)
        self.run_btn.pack(side=tk.LEFT, padx=5)

        el_frame = ttk.LabelFrame(main, text="Selected elements", padding=5)
        el_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        self.elements_listbox = tk.Listbox(el_frame, height=6, selectmode=tk.SINGLE)
        self.elements_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(el_frame, orient=tk.VERTICAL, command=self.elements_listbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.elements_listbox.config(yscrollcommand=sb.set)
        btn_col = ttk.Frame(el_frame)
        btn_col.pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(btn_col, text="Remove", command=self._remove_element).pack(pady=2)

        # --- Status ---
        status_frame = ttk.Frame(main)
        status_frame.pack(fill=tk.X)
        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor="w").pack(fill=tk.X)

        # --- Menu ---
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Settings…", command=self._settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._about)

    def _refresh_profiles(self):
        profiles = list_profiles(self.conn)
        self._profiles = profiles
        names = [p["name"] for p in profiles]
        self.profile_combo["values"] = names
        if names and self._current_profile_id is None:
            self.profile_combo.current(0)
            self._on_profile_selected(None)
        elif self._current_profile_id:
            for i, p in enumerate(profiles):
                if p["id"] == self._current_profile_id:
                    self.profile_combo.current(i)
                    break

    def _refresh_browsers(self):
        browsers = list_browsers(self.conn)
        self._browsers = browsers
        self.browser_combo["values"] = [
            f"{b['display_name']} ({b.get('install_status', '?')})" for b in browsers
        ]
        if browsers:
            self.browser_combo.current(0)
        self._on_browser_combo_change()

    def _on_browser_combo_change(self):
        idx = self.browser_combo.current()
        if idx < 0 or not self._browsers:
            return
        b = self._browsers[idx]
        status = b.get("install_status") or "?"
        self.browser_status_var.set(status)

    def _on_profile_selected(self, event):
        idx = self.profile_combo.current()
        if idx < 0 or not self._profiles:
            self._current_profile_id = None
            return
        p = self._profiles[idx]
        self._current_profile_id = p["id"]
        self.url_var.set(p.get("url") or "https://")
        browser_id = p.get("browser_id")
        for i, b in enumerate(self._browsers):
            if b["id"] == browser_id:
                self.browser_combo.current(i)
                break
        self._on_browser_combo_change()
        self._refresh_elements_list()

    def _refresh_elements_list(self):
        self.elements_listbox.delete(0, tk.END)
        if self._current_profile_id is None:
            return
        for el in list_profile_elements(self.conn, self._current_profile_id):
            label = f"{el['column_name']} ← {el['selector'][:40]}{'…' if len(el['selector']) > 40 else ''} ({el['extract_type']})"
            self.elements_listbox.insert(tk.END, label)

    def _new_profile(self):
        opts = ask_profile(self.root, self._browsers)
        if not opts:
            return
        name, url, browser_id = opts
        pid = create_profile(self.conn, name, url, browser_id)
        self._current_profile_id = pid
        self._refresh_profiles()
        self._refresh_elements_list()
        self.status_var.set(f"Created profile «{name}».")

    def _install_browser(self):
        idx = self.browser_combo.current()
        if idx < 0 or not self._browsers:
            messagebox.showinfo("No browser", "Select a browser.", parent=self.root)
            return
        b = self._browsers[idx]
        browser_id = b["id"]
        self.status_var.set("Installing browser…")
        self.install_btn.config(state="disabled")

        def work():
            # Use a connection created in this thread; SQLite connections are not thread-safe.
            conn = ensure_db()
            try:
                ok, err = ensure_browser_installed(conn, browser_id)
                self.root.after(0, lambda: self._on_install_done(ok, err))
            finally:
                conn.close()

        threading.Thread(target=work, daemon=True).start()

    def _on_install_done(self, ok: bool, err: str):
        self.install_btn.config(state="normal")
        self._refresh_browsers()
        if ok:
            self.status_var.set("Browser ready.")
        else:
            self.status_var.set("Install failed.")
            messagebox.showerror("Install failed", err or "Unknown error.", parent=self.root)

    def _start_picker(self):
        if self._current_profile_id is None:
            messagebox.showinfo("No profile", "Create or select a profile first.", parent=self.root)
            return
        url = self.url_var.get().strip()
        if not url or url == "https://":
            messagebox.showinfo("No URL", "Enter the URL to open in the picker.", parent=self.root)
            return
        idx = self.browser_combo.current()
        if idx < 0 or not self._browsers:
            messagebox.showinfo("No browser", "Select a browser.", parent=self.root)
            return
        b = self._browsers[idx]
        if (b.get("install_status") or "") != "installed":
            messagebox.showinfo("Browser not installed", "Install the browser first.", parent=self.root)
            return

        # Persist URL and browser to profile
        update_profile(self.conn, self._current_profile_id, url=url, browser_id=b["id"])

        self.picker_btn.config(state="disabled")
        self.status_var.set("Opening browser…")
        self.root.update_idletasks()

        # Run picker on main thread; Playwright sync API must not be used from another thread.
        try:
            session = ElementPickerSession(url, b["executable_path"], {"headless": False})
            session.__enter__()
            self._picker_session = session
            self.status_var.set("Click an element in the browser window. Close the browser when done.")
            self._picker_poll()
        except Exception as e:
            self._picker_session = None
            self.picker_btn.config(state="normal")
            self.status_var.set("Picker failed.")
            messagebox.showerror("Picker error", str(e), parent=self.root)

    def _picker_poll(self):
        """Poll for clicks and closed browser; runs on main thread. Playwright must stay on this thread."""
        session = self._picker_session
        if session is None:
            return
        try:
            if session.is_page_closed():
                self._picker_cleanup()
                return
            result = session.get_next_selector(timeout=0)
            if result is PICKER_CLOSED:
                self._picker_cleanup()
                return
            if result is not None:
                selector, inspection = result
                self._on_picker_selector(selector, inspection)
        except Exception:
            # Keep polling so further selections work; do not leave button stuck disabled
            pass
        # Always schedule next poll unless we returned above (cleanup)
        self._picker_after_id = self.root.after(150, self._picker_poll)

    def _picker_cleanup(self):
        if self._picker_after_id:
            self.root.after_cancel(self._picker_after_id)
            self._picker_after_id = None
        session = self._picker_session
        if session is not None:
            try:
                session.__exit__(None, None, None)
            except Exception:
                pass
            self._picker_session = None
        self.picker_btn.config(state="normal")
        self.status_var.set("Picker closed.")

    def _poll_picker_queue(self):
        try:
            while True:
                msg = self._picker_queue.get_nowait()
                if msg[0] == "selector":
                    self._on_picker_selector(msg[1])
                elif msg[0] == "error":
                    messagebox.showerror("Picker error", msg[1], parent=self.root)
        except queue.Empty:
            pass
        self._after_id = self.root.after(200, self._poll_picker_queue)

    def _on_picker_selector(self, selector: str, inspection=None):
        existing_columns = []
        if self._current_profile_id is not None:
            for el in list_profile_elements(self.conn, self._current_profile_id):
                name = (el.get("column_name") or "").strip()
                if name:
                    existing_columns.append(name)
        opts = ask_element_options(self.root, selector, inspection, existing_columns)
        if not opts:
            return
        col, ext, arg = opts
        session = self._picker_session
        if session and self._current_profile_id:
            try:
                session.add_to_profile(
                    self.conn, self._current_profile_id, selector, col,
                    extract_type=ext, extract_arg=arg,
                )
                self._refresh_elements_list()
                self.status_var.set(f"Added element «{col}».")
            except sqlite3.IntegrityError:
                messagebox.showerror(
                    "Duplicate column",
                    "This column name already exists in the profile. Choose a different name.",
                    parent=self.root,
                )

    def _picker_finished(self):
        """Called when picker ends (e.g. from queue-based flow); ensure cleanup."""
        self._picker_cleanup()

    def _remove_element(self):
        if self._current_profile_id is None:
            return
        sel = self.elements_listbox.curselection()
        if not sel:
            messagebox.showinfo("No selection", "Select an element to remove.", parent=self.root)
            return
        idx = sel[0]
        els = list_profile_elements(self.conn, self._current_profile_id)
        if idx >= len(els):
            return
        el_id = els[idx]["id"]
        remove_profile_element(self.conn, el_id)
        self._refresh_elements_list()
        self.status_var.set("Element removed.")

    def _run_scrape(self):
        if self._current_profile_id is None:
            messagebox.showinfo("No profile", "Select a profile first.", parent=self.root)
            return
        els = list_profile_elements(self.conn, self._current_profile_id)
        if not els:
            messagebox.showinfo("No elements", "Add at least one element to scrape.", parent=self.root)
            return
        # Persist current URL to profile
        url = self.url_var.get().strip()
        if url and url != "https://":
            idx = self.browser_combo.current()
            browser_id = self._browsers[idx]["id"] if idx >= 0 and self._browsers else None
            if browser_id is not None:
                update_profile(self.conn, self._current_profile_id, url=url, browser_id=browser_id)

        self.run_btn.config(state="disabled")
        self.status_var.set("Running scrape…")
        pid = self._current_profile_id

        def work():
            result = run_scrape(pid, conn=None)
            self.root.after(0, lambda: self._on_scrape_done(result))

        threading.Thread(target=work, daemon=True).start()

    def _on_scrape_done(self, result: Dict[str, Any]):
        self.run_btn.config(state="normal")
        if result.get("success"):
            path = result.get("output_csv_path", "")
            count = result.get("row_count", 0)
            self.status_var.set(f"Done. {count} rows → {path}")
            messagebox.showinfo("Scrape complete", f"Saved {count} rows to:\n{path}", parent=self.root)
        else:
            err = result.get("error_message") or "Unknown error"
            self.status_var.set("Scrape failed.")
            messagebox.showerror("Scrape failed", err, parent=self.root)

    def _settings(self):
        current = get_config_default(
            self.conn, OUTPUT_DIR_CONFIG_KEY,
            str(get_config_dir() / "scrapes"),
        )
        path = ask_output_dir(self.root, current)
        if path is not None:
            set_config(self.conn, OUTPUT_DIR_CONFIG_KEY, path)
            self.status_var.set(f"Output directory: {path}")

    def _about(self):
        messagebox.showinfo(
            "About uscraper",
            "uscraper — Universal Web Scraper\n\n"
            "Select a profile, URL, and browser. Use «Select elements» to pick what to scrape, then «Run scrape».",
            parent=self.root,
        )

    def run(self):
        self.browser_combo.bind("<<ComboboxSelected>>", lambda e: self._on_browser_combo_change())
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self):
        if self._after_id:
            self.root.after_cancel(self._after_id)
        self.conn.close()
        self.root.destroy()


def run_gui() -> None:
    """Launch the desktop GUI (Tkinter)."""
    app = MainWindow()
    app.run()
