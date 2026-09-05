"""
Wraps a ttk.Treeview with scrollbars, column sorting, ID-prefix filtering,
and CSV/Excel export.

Replaces what used to be several free functions in TAapp.py operating on
a global `tableView`: selectTable()'s tree-building code, sortColumns(),
updateHeaders(), filterTreeView(), toCSV(), toExcel(), getCurrentTableView().

Design choice: TableView only knows about display state (which rows/columns
it currently holds). It does not talk to the database directly — the
controller (MainWindow) is responsible for querying the DB and calling
`populate()`. This keeps the widget reusable and testable without a live
DB connection, and avoids repeating the DB query in both selectTable() and
filterTreeView() like the original code did.
"""
from tkinter import ttk

from services.export_service import ExportService
from logging_setup import get_logger

logger = get_logger("ui.table_view")


class TableView:
    def __init__(self, parent, export_service: ExportService = None):
        self.parent = parent
        self.export_service = export_service or ExportService()

        self.frame = ttk.Frame(parent)
        self._sort_states = {}
        self.tree = None
        self._all_rows = []  # last full (unfiltered) dataset, for client-side filtering
        self.columns = []

    # ---- construction ----
    def render(self, columns, rows, column_widths: dict = None):
        """(Re)builds the Treeview with the given columns/rows.
        column_widths: optional {column_name_lower: (width, stretch, anchor)}."""
        for widget in self.frame.winfo_children():
            widget.destroy()

        self.columns = list(columns)
        self._all_rows = list(rows)
        column_widths = column_widths or {}

        y_scroll = ttk.Scrollbar(self.frame, orient="vertical")
        y_scroll.pack(side="right", fill="y")
        x_scroll = ttk.Scrollbar(self.frame, orient="horizontal")
        x_scroll.pack(side="bottom", fill="x")

        self.tree = ttk.Treeview(
            self.frame, columns=self.columns, show="headings", height=10,
            yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set,
        )

        for col in self.columns:
            width, stretch, anchor = column_widths.get(
                col.lower(), (150, True, "center")
            )
            self.tree.column(col, width=width, stretch=stretch, anchor=anchor)
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_by(c))

        self.tree.pack(fill="both", expand=True)
        y_scroll.config(command=self.tree.yview)
        x_scroll.config(command=self.tree.xview)

        self._insert_rows(rows)

    def _insert_rows(self, rows):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in rows:
            self.tree.insert("", "end", values=list(row))

    # ---- sorting ----
    def sort_by(self, column):
        reverse = self._sort_states.get(column, False)
        data = []
        for item_id in self.tree.get_children(""):
            raw = self.tree.set(item_id, column)
            data.append((raw, item_id))

        def sort_key(pair):
            value = pair[0]
            try:
                return float(value)
            except (TypeError, ValueError):
                return value.lower() if isinstance(value, str) else value

        data.sort(key=sort_key, reverse=reverse)
        for index, (_, item_id) in enumerate(data):
            self.tree.move(item_id, "", index)

        self._sort_states[column] = not reverse
        self._update_headers(column, reverse)
        self.tree.heading(column, command=lambda: self.sort_by(column))

    def _update_headers(self, sorted_column, reverse):
        for col in self.columns:
            label = col
            if col == sorted_column:
                arrow = "\u25bc" if reverse else "\u25b2"
                label = f"{col} {arrow}"
            self.tree.heading(col, text=label)

    # ---- filtering (client-side, over the last loaded dataset) ----
    def filter_by_sid_prefix(self, prefix: str, sid_column_index: int = 0):
        prefix = (prefix or "").strip()
        if not prefix:
            self._insert_rows(self._all_rows)
            return
        filtered = [
            row for row in self._all_rows
            if str(row[sid_column_index]).startswith(prefix)
        ]
        self._insert_rows(filtered)

    # ---- export ----
    def export_csv(self, filepath: str = None):
        rows = self._current_rows()
        return self.export_service.export_to_csv(self.columns, rows, filepath=filepath)

    def export_excel(self, filepath: str = None):
        rows = self._current_rows()
        return self.export_service.export_to_excel(self.columns, rows, filepath=filepath)

    def _current_rows(self):
        return [self.tree.item(iid, "values") for iid in self.tree.get_children("")]

    # ---- selection helpers ----
    def get_selected_values(self):
        selected = self.tree.selection()
        if not selected:
            return None
        return self.tree.item(selected[0], "values")

    def select_row_by_sid(self, sid, sid_column_index: int = 0):
        for item_id in self.tree.get_children():
            values = self.tree.item(item_id, "values")
            if values and str(values[sid_column_index]) == str(sid):
                self.tree.selection_set(item_id)
                self.tree.see(item_id)
                return
