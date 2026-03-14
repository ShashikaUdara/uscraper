"""Simple modal dialogs for profile, element options, and settings."""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from typing import Optional, Tuple, List, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from uscraper.engine.inspect import ElementHierarchy, ElementInspection

# Truncate attribute value in dropdown display (Phase 4b)
ATTR_DISPLAY_VALUE_LEN = 40


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


def _column_suggestions(inspection: Optional["ElementInspection"], existing_columns: Optional[List[str]] = None) -> Tuple[List[str], str]:
    """Build suggested column names from inspection and existing columns. Returns (all_options, default)."""
    suggestions: List[str] = []
    default = "column"
    if inspection:
        tag = (inspection.tag_name or "").lower()
        attrs = inspection.attributes or []
        attr_names = [a["name"].lower() for a in attrs]
        if tag == "a" and "href" in attr_names:
            suggestions.append("link")
        if tag == "img":
            if "src" in attr_names:
                suggestions.append("image_src")
            if "alt" in attr_names:
                suggestions.append("image_alt")
        if not suggestions and attrs:
            first = attrs[0]["name"].lower()
            suggestions.append(f"{tag}_{first}" if tag else first)
        suggestions.append("inner_text")
        suggestions.append("html")
        seen = set(suggestions)
        for c in existing_columns or []:
            if c and (c not in seen):
                seen.add(c)
                suggestions.append(c)
        default = suggestions[0] if suggestions else "column"
    else:
        suggestions = list(existing_columns or [])
        if "inner_text" not in suggestions:
            suggestions.append("inner_text")
        if "html" not in suggestions:
            suggestions.append("html")
        if not suggestions:
            suggestions = ["inner_text", "html", "column"]
        default = suggestions[0] if suggestions else "column"
    return (suggestions, default)


def _suggest_extract_and_attr(inspection: Optional["ElementInspection"]) -> Tuple[str, Optional[str]]:
    """Suggest extract_type and extract_arg from inspection. Returns (extract_type, extract_arg)."""
    if not inspection or not inspection.attributes:
        return ("text", None)
    tag = (inspection.tag_name or "").lower()
    attrs = inspection.attributes
    if tag == "a" and any(a["name"].lower() == "href" for a in attrs):
        return ("attribute", "href")
    if tag == "img" and any(a["name"].lower() == "src" for a in attrs):
        return ("attribute", "src")
    return ("text", None)


def _format_hierarchy_node(node: Any) -> str:
    """Format a HierarchyNode for display: tag + id + class."""
    tag = getattr(node, "tag_name", "") or ""
    id_val = getattr(node, "id", "") or ""
    cls = getattr(node, "class_name", "") or ""
    parts = [f"<{tag}>" if tag else "?"]
    if id_val:
        parts.append(f"#{id_val}")
    if cls:
        parts.append(f".{cls.replace(' ', '.')[:40]}")
    return " ".join(parts)


def ask_element_options(
    parent,
    selector: str,
    inspection: Optional["ElementInspection"] = None,
    existing_columns: Optional[List[str]] = None,
    hierarchy: Optional["ElementHierarchy"] = None,
    match_count: Optional[int] = None,
) -> Optional[Tuple[str, str, Optional[str]]]:
    """Return (column_name, extract_type, extract_arg) or None. extract_arg used when type is 'attribute'.
    inspection: optional ElementInspection from picker (Phase 4a); used for dropdowns and pre-fill.
    existing_columns: optional list of column names already in the profile (for suggestions and duplicate check).
    hierarchy: optional ElementHierarchy from picker (Phase 5b); shown as path from root → clicked → children.
    match_count: optional number of elements matching the selector on the current page (Phase 5c)."""
    from uscraper.engine.inspect import ElementHierarchy as EH, ElementInspection as EI

    result = [None]
    inspection = inspection if isinstance(inspection, EI) else None
    existing_columns = list(existing_columns or [])
    hierarchy = hierarchy if isinstance(hierarchy, EH) else None
    match_count = int(match_count) if match_count is not None else None

    d = tk.Toplevel(parent)
    d.title("Element options")
    d.transient(parent)
    d.grab_set()
    d.geometry("500x480")

    row = 0

    # Element hierarchy (Phase 5b): path from root → clicked → children
    if hierarchy:
        ttk.Label(d, text="Element hierarchy:", font=("", 9, "bold")).grid(row=row, column=0, sticky="nw", padx=5, pady=(8, 2))
        row += 1
        hier_lines: List[str] = []
        for depth, node in enumerate(hierarchy.path_from_root):
            indent = "  " * depth
            line = indent + _format_hierarchy_node(node)
            if depth == len(hierarchy.path_from_root) - 1 and hierarchy.path_from_root:
                line += "  ← clicked"
            hier_lines.append(line)
        if hierarchy.children:
            depth_clicked = len(hierarchy.path_from_root) - 1 if hierarchy.path_from_root else 0
            for node in hierarchy.children:
                hier_lines.append("  " * (depth_clicked + 1) + _format_hierarchy_node(node))
        hier_text = "\n".join(hier_lines) if hier_lines else "(none)"
        hier_frame = ttk.Frame(d)
        hier_frame.grid(row=row, column=0, columnspan=2, sticky="nsew", padx=5, pady=(0, 8))
        hier_box = tk.Text(hier_frame, height=6, width=70, wrap="word", state="disabled", font=("TkDefaultFont", 9))
        hier_box.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(hier_frame, command=hier_box.yview)
        sb.pack(side="right", fill="y")
        hier_box.config(yscrollcommand=sb.set)
        hier_box.config(state="normal")
        hier_box.insert("1.0", hier_text)
        hier_box.config(state="disabled")
        row += 1

    # Element preview (Phase 4b)
    if inspection:
        ttk.Label(d, text="Element preview:", font=("", 9, "bold")).grid(row=row, column=0, sticky="nw", padx=5, pady=(8, 2))
        row += 1
        preview_parts = [f"<{inspection.tag_name}>"]
        for a in inspection.attributes or []:
            if a["name"].lower() in ("id", "class") and a["value"]:
                preview_parts.append(f'{a["name"]}={a["value"][:30]}')
        preview_line = " ".join(preview_parts)
        ttk.Label(d, text=preview_line, wraplength=400).grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=(0, 2))
        row += 1
        if inspection.inner_text_preview:
            ttk.Label(d, text=inspection.inner_text_preview[:80], wraplength=400, foreground="gray").grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=(0, 8))
        row += 1

    # Selector with Copy
    ttk.Label(d, text="Selector:").grid(row=row, column=0, sticky="w", padx=5, pady=5)
    sel_frame = ttk.Frame(d)
    sel_frame.grid(row=row, column=1, sticky="w", padx=5, pady=5)
    sel_text = selector[:80] + ("..." if len(selector) > 80 else "")
    ttk.Label(sel_frame, text=sel_text, wraplength=320).pack(side="left")
    def copy_sel():
        d.clipboard_clear()
        d.clipboard_append(selector)
    ttk.Button(sel_frame, text="Copy", command=copy_sel, width=6).pack(side="left", padx=(8, 0))
    row += 1

    # Phase 5c: clarify that scraping finds all matching elements
    scrape_all_msg = "When you run a scrape, the tool will find all elements on the page that match this selector and extract the chosen field for each."
    ttk.Label(d, text=scrape_all_msg, wraplength=450, foreground="gray").grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=(0, 4))
    row += 1
    if match_count is not None:
        ttk.Label(d, text=f"This selector matches {match_count} element(s) on the current page.", wraplength=450, font=("", 9, "bold")).grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=(0, 8))
        row += 1

    # Column name: combobox (dropdown + free text)
    col_suggestions, col_default = _column_suggestions(inspection, existing_columns)
    ttk.Label(d, text="Column name:").grid(row=row, column=0, sticky="w", padx=5, pady=5)
    col_var = tk.StringVar(value=col_default)
    col_combo = ttk.Combobox(d, textvariable=col_var, values=col_suggestions, width=38)
    col_combo.grid(row=row, column=1, sticky="w", padx=5, pady=5)
    row += 1

    # Extract type
    ttk.Label(d, text="Extract:").grid(row=row, column=0, sticky="w", padx=5, pady=5)
    ext_default, attr_default = _suggest_extract_and_attr(inspection)
    type_var = tk.StringVar(value=ext_default)
    type_combo = ttk.Combobox(d, textvariable=type_var, values=["text", "attribute", "html"], state="readonly", width=12)
    type_combo.grid(row=row, column=1, sticky="w", padx=5, pady=5)
    type_combo.current(["text", "attribute", "html"].index(ext_default))
    row += 1

    # Attribute name (when extract type = attribute): dropdown or manual entry
    attr_label = ttk.Label(d, text="Attribute name:")
    attr_label.grid(row=row, column=0, sticky="w", padx=5, pady=5)
    attr_var = tk.StringVar(value=attr_default or "href")
    attr_names: List[str] = []
    attr_display_values: List[str] = []
    attr_combo_ref: List[Optional[ttk.Combobox]] = [None]
    if inspection and inspection.attributes:
        for a in inspection.attributes:
            attr_names.append(a["name"])
            v = (a["value"] or "").strip()
            if len(v) > ATTR_DISPLAY_VALUE_LEN:
                v = v[:ATTR_DISPLAY_VALUE_LEN] + "..."
            attr_display_values.append(f"{a['name']} → {v}")
    attr_frame = ttk.Frame(d)
    attr_frame.grid(row=row, column=1, sticky="w", padx=5, pady=5)
    full_attr_values: List[str] = []
    if attr_display_values:
        full_attr_values = [(a["value"] or "") for a in (inspection.attributes or [])]
        attr_combo = ttk.Combobox(attr_frame, values=attr_display_values, state="readonly", width=36)
        attr_combo.pack(side="left")
        attr_combo_ref[0] = attr_combo
        idx = 0
        if attr_default and attr_default in attr_names:
            idx = attr_names.index(attr_default)
        attr_combo.current(idx)
        def view_full_attr():
            combo = attr_combo_ref[0]
            if combo is not None and full_attr_values:
                try:
                    i = combo.current()
                    if 0 <= i < len(full_attr_values):
                        msg = full_attr_values[i] or "(empty)"
                        messagebox.showinfo("Attribute value", msg[:2000] + ("..." if len(msg) > 2000 else ""), parent=d)
                except Exception:
                    pass
        ttk.Button(attr_frame, text="View full", command=view_full_attr, width=8).pack(side="left", padx=(6, 0))
    else:
        ttk.Label(attr_frame, text="No attributes").pack(side="left")
        ttk.Entry(attr_frame, textvariable=attr_var, width=20).pack(side="left", padx=(8, 0))
    row += 1

    def on_extract_type_change(*_):
        if type_var.get() == "attribute":
            attr_label.grid()
            attr_frame.grid()
        else:
            attr_label.grid_remove()
            attr_frame.grid_remove()
    type_var.trace_add("write", on_extract_type_change)
    if type_var.get() != "attribute":
        attr_label.grid_remove()
        attr_frame.grid_remove()

    def get_selected_attr() -> str:
        if type_var.get() != "attribute":
            return attr_var.get().strip()
        combo = attr_combo_ref[0]
        if combo is not None and attr_names:
            try:
                i = combo.current()
                if 0 <= i < len(attr_names):
                    return attr_names[i]
            except Exception:
                pass
        return attr_var.get().strip()

    def ok():
        col = col_var.get().strip()
        if not col:
            messagebox.showwarning("Missing column", "Enter a column name.", parent=d)
            return
        if existing_columns and col in existing_columns:
            if not messagebox.askyesno(
                "Duplicate column name",
                "This column name is already used in this profile. Use it anyway?",
                icon="warning",
                parent=d,
            ):
                return
        ext = type_var.get().strip() or "text"
        arg = get_selected_attr() if ext == "attribute" else None
        if ext == "attribute" and not arg:
            arg = "href"
        result[0] = (col, ext, arg)
        d.destroy()

    def cancel():
        d.destroy()

    btn_frame = ttk.Frame(d)
    btn_frame.grid(row=row, column=0, columnspan=2, pady=15)
    ttk.Button(btn_frame, text="OK", command=ok).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Cancel", command=cancel).pack(side="left", padx=5)

    # Keyboard: Enter confirms, Escape cancels (Phase 4d)
    d.bind("<Return>", lambda e: ok())
    d.bind("<Escape>", lambda e: cancel())
    d.after(10, col_combo.focus_set)

    d.wait_window()
    return result[0]


def ask_output_dir(parent, current: str) -> Optional[str]:
    """Return selected directory path or None."""
    path = filedialog.askdirectory(parent=parent, title="Output directory for CSV files", initialdir=current or None)
    return path if path else None
