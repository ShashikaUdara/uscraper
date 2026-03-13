"""Simple modal dialogs for profile, element options, and settings."""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from typing import Optional, Tuple, List, Any


def ask_profile(parent, browsers: List[dict]) -> Optional[Tuple[str, str, int]]:
    """Return (name, url, browser_id) or None if cancelled."""
    result = [None]

    d = tk.Toplevel(parent)
    d.title("New profile")
    d.transient(parent)
    d.grab_set()
    d.geometry("420x180")

    ttk.Label(d, text="Profile name:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
    name_var = tk.StringVar()
    ttk.Entry(d, textvariable=name_var, width=40).grid(row=0, column=1, padx=5, pady=5)

    ttk.Label(d, text="URL:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
    url_var = tk.StringVar(value="https://")
    ttk.Entry(d, textvariable=url_var, width=40).grid(row=1, column=1, padx=5, pady=5)

    ttk.Label(d, text="Browser:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
    browser_ids = [b["id"] for b in browsers]
    display_names = [f"{b['display_name']} ({b.get('install_status', '?')})" for b in browsers]
    browser_var = tk.StringVar(value=display_names[0] if display_names else "")
    combo = ttk.Combobox(d, textvariable=browser_var, values=display_names, state="readonly", width=38)
    combo.grid(row=2, column=1, padx=5, pady=5)
    if display_names:
        combo.current(0)

    def ok():
        name = name_var.get().strip()
        url = url_var.get().strip()
        if not name:
            messagebox.showwarning("Missing name", "Enter a profile name.", parent=d)
            return
        if not url or url == "https://":
            messagebox.showwarning("Missing URL", "Enter a valid URL.", parent=d)
            return
        idx = combo.current()
        if idx < 0:
            messagebox.showwarning("No browser", "Select a browser.", parent=d)
            return
        result[0] = (name, url, browser_ids[idx])
        d.destroy()

    def cancel():
        d.destroy()

    btn_frame = ttk.Frame(d)
    btn_frame.grid(row=3, column=0, columnspan=2, pady=15)
    ttk.Button(btn_frame, text="OK", command=ok).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Cancel", command=cancel).pack(side="left", padx=5)

    d.wait_window()
    return result[0]


def ask_element_options(parent, selector: str) -> Optional[Tuple[str, str, Optional[str]]]:
    """Return (column_name, extract_type, extract_arg) or None. extract_arg used when type is 'attribute'."""
    result = [None]

    d = tk.Toplevel(parent)
    d.title("Element options")
    d.transient(parent)
    d.grab_set()
    d.geometry("400x200")

    ttk.Label(d, text="Selector:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
    ttk.Label(d, text=selector[:60] + ("..." if len(selector) > 60 else ""), wraplength=320).grid(row=0, column=1, sticky="w", padx=5, pady=5)

    ttk.Label(d, text="Column name:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
    col_var = tk.StringVar()
    ttk.Entry(d, textvariable=col_var, width=35).grid(row=1, column=1, padx=5, pady=5)

    ttk.Label(d, text="Extract:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
    type_var = tk.StringVar(value="text")
    type_combo = ttk.Combobox(d, textvariable=type_var, values=["text", "attribute", "html"], state="readonly", width=12)
    type_combo.grid(row=2, column=1, sticky="w", padx=5, pady=5)
    type_combo.current(0)

    ttk.Label(d, text="Attribute name (if attribute):").grid(row=3, column=0, sticky="w", padx=5, pady=5)
    attr_var = tk.StringVar(value="href")
    ttk.Entry(d, textvariable=attr_var, width=20).grid(row=3, column=1, sticky="w", padx=5, pady=5)

    def ok():
        col = col_var.get().strip()
        if not col:
            messagebox.showwarning("Missing column", "Enter a column name.", parent=d)
            return
        ext = type_var.get().strip() or "text"
        arg = attr_var.get().strip() if ext == "attribute" else None
        if ext == "attribute" and not arg:
            arg = "href"
        result[0] = (col, ext, arg)
        d.destroy()

    def cancel():
        d.destroy()

    btn_frame = ttk.Frame(d)
    btn_frame.grid(row=4, column=0, columnspan=2, pady=15)
    ttk.Button(btn_frame, text="OK", command=ok).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Cancel", command=cancel).pack(side="left", padx=5)

    d.wait_window()
    return result[0]


def ask_output_dir(parent, current: str) -> Optional[str]:
    """Return selected directory path or None."""
    path = filedialog.askdirectory(parent=parent, title="Output directory for CSV files", initialdir=current or None)
    return path if path else None
