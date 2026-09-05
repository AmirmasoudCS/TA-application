"""
MainWindow: the application's controller/root window.

This replaces essentially all of the original TAapp.py: the module-level
globals (main_window, tableView, course_window, escMenuIsOpen, sortStates,
etc.) are now instance attributes, and the free functions
(selectTable, addItem, removeItem, finalizeCourse, filterTreeView,
lookupStudentName, toggleEscMenu, ...) are now methods.

The controller owns: the Tk root, the Database, the Theme, the current
course/filename state, and a TableView widget. It delegates actual widget
construction for popups to the classes in ui/windows/, and table rendering
to ui/widgets/table_view.TableView.
"""
from tkinter import IntVar, StringVar, Tk, Toplevel, Frame
from tkinter import font, messagebox, ttk
from tkinter import filedialog

from config import DB_PATH
from db.database import Database
from services.roster_import_service import RosterImportService
from services.export_service import ExportService
from services.stats_service import StatsService
from ui.theme import Theme
from ui.widgets.table_view import TableView
from ui.windows.course_setup_window import start_course_setup
from ui.windows.comment_window import CommentWindow
from ui.windows.update_window import UpdateWindow
from ui.windows.histogram_window import HistogramWindow
from ui.windows.settings_window import SettingsWindow
from logging_setup import get_logger

logger = get_logger("ui.main_window")

_COLUMN_WIDTHS = {
    "score": (80, False, "center"),
    "sid": (80, False, "center"),
    "calculated": (80, False, "center"),
    "comment": (400, True, "w"),
}


class MainWindow:
    def __init__(self):
        self.root = Tk()
        self.root.option_add("*TEntry*Font", ("Inter", 12, "bold"))
        self.root.option_add("*TEntry*justify", "center")
        self.root.title("Teacher Assistant Application")
        self.root.geometry("1400x800")
        self.root.attributes("-fullscreen", True)
        self.root.resizable(0, 0)
        for r in range(5):
            self.root.rowconfigure(r, weight=0)
        self.root.rowconfigure(2, weight=1)
        for c in range(11):
            self.root.columnconfigure(c, weight=1)

        self.theme = Theme()
        self.theme.load_theme()
        self.theme.apply(self.root)

        self.db = Database(DB_PATH)
        self.roster_service = RosterImportService()
        self.export_service = ExportService()

        self.course_name = None
        self.filename = None
        self.table_name = StringVar(self.root)
        self.id_var = IntVar(self.root)
        self.score_var = IntVar(self.root)
        self.remove_id_var = IntVar(self.root)
        self.search_var = StringVar(self.root)
        self.base_grade_var = IntVar(self.root)

        self.table_view = None
        self.table_frame_outer = None
        self.stats_label = None
        self.name_lookup_label = None
        self.id_entry = None
        self.score_entry = None

        self.escape_menu = None
        self.esc_menu_open = False

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---- lifecycle ----
    def run(self):
        start_course_setup(self.root, self.theme, self._on_course_ready, self.roster_service)
        self.root.mainloop()

    def on_close(self):
        logger.info("Closing application.")
        try:
            self.db.close()
        except Exception:
            logger.exception("Error closing database on shutdown.")
        self.root.destroy()

    # ---- course setup ----
    def _on_course_ready(self, course_name: str, roster_filename: str):
        self.course_name = course_name
        self.filename = roster_filename

        self.db.courses.create_students_table(course_name)
        try:
            students = self.roster_service.parse_roster_file(roster_filename)
            self.db.students.insert_students(course_name, students)
        except Exception as e:
            logger.exception("Failed to import roster %s", roster_filename)
            messagebox.showerror(
                "Roster Import Error",
                f"Could not import roster '{roster_filename}':\n{e}",
            )
        self.db.courses.create_assessment_info_table(course_name)

        self._build_main_ui()

    def _reopen_course_setup(self, course_name: str, filename: str):
        # Used by Settings -> "Apply New Course".
        self._on_course_ready(course_name, filename)

    # ---- main UI construction ----
    def _build_main_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        self.root.rowconfigure(2, weight=1)

        info_frame = ttk.LabelFrame(self.root, padding=(5, 2), text="Information")
        add_frame = ttk.LabelFrame(self.root, text="Add Students", padding=(5, 2))
        remove_frame = ttk.LabelFrame(self.root, text="Remove Students", padding=(5, 2))
        select_frame = ttk.LabelFrame(self.root, text="Select Table", padding=(5, 2))

        info_frame.grid(row=0, column=0, columnspan=10, sticky="ew", padx=20, pady=5)
        select_frame.grid(row=1, column=0, columnspan=10, sticky="ew", padx=20, pady=5)
        add_frame.grid(row=3, column=0, columnspan=10, sticky="ew", padx=20, pady=5)
        remove_frame.grid(row=4, column=0, columnspan=10, sticky="ew", padx=20, pady=5)

        table_outer = ttk.Frame(self.root, borderwidth=1, relief="solid")
        table_outer.grid(row=2, column=0, columnspan=10, sticky="nsew", padx=10, pady=5)
        table_outer.grid_rowconfigure(0, weight=1)
        table_outer.grid_columnconfigure(0, weight=1)
        self.table_view = TableView(table_outer, self.export_service)
        self.table_view.frame.grid(row=0, column=0, sticky="nsew")

        for frame in (add_frame, remove_frame, select_frame, info_frame):
            for c in range(10):
                frame.grid_columnconfigure(c, weight=1)

        # --- information frame ---
        ttk.Label(info_frame, text=f"Course : {self.course_name}").grid(row=0, column=0, padx=10)
        ttk.Label(info_frame, text=f"Filename : {self.filename}").grid(row=1, column=0, padx=10)

        ttk.Label(info_frame, text="Search by ID").grid(row=0, column=3, padx=10, pady=10)
        search_entry = ttk.Entry(info_frame, textvariable=self.search_var, width=20)
        search_entry.grid(row=1, column=3, pady=(0, 10), padx=10)
        search_entry.bind("<KeyRelease>", lambda e: self.table_view.filter_by_sid_prefix(self.search_var.get()))

        ttk.Button(info_frame, text="Export to CSV", width=12, command=self._export_csv).grid(
            row=1, column=9, sticky="e", padx=20, pady=5
        )
        ttk.Button(info_frame, text="Export to Excel", width=15, command=self._export_excel).grid(
            row=1, column=8, sticky="e", padx=5, pady=5
        )
        ttk.Button(info_frame, text="Finalize", width=12, command=self._finalize_course).grid(
            row=0, column=9, padx=20, sticky="e"
        )

        # --- select-table frame ---
        ttk.Label(select_frame, text="Table to present : ").grid(row=0, column=0, padx=10)
        table_entry = ttk.Entry(select_frame, textvariable=self.table_name, width=10)
        table_entry.grid(row=1, column=0, pady=15)
        table_entry.bind("<Return>", lambda e: self.select_table())
        ttk.Button(select_frame, text="Select Table", width=15, command=self.select_table).grid(row=1, column=1, padx=10)
        table_entry.focus_set()

        self.stats_label = ttk.Label(select_frame, text="")
        self.stats_label.grid(row=1, column=2, sticky="ew", padx=10, pady=5)
        ttk.Button(select_frame, text="Show Histogram", command=self._show_histogram).grid(row=1, column=9, padx=5, pady=5)

        # --- add frame ---
        ttk.Label(add_frame, text="ID:").grid(row=0, column=0, padx=5)
        self.id_entry = ttk.Entry(add_frame, textvariable=self.id_var, width=10)
        self.id_entry.grid(row=0, column=1, padx=10)
        self.id_entry.bind("<Return>", lambda e: self.score_entry.focus_set())
        self.id_entry.bind("<KeyRelease>", self._lookup_student_name)

        self.name_lookup_label = ttk.Label(add_frame, text="Name: ---")
        self.name_lookup_label.grid(row=0, column=2, padx=5)

        ttk.Label(add_frame, text="Score:").grid(row=0, column=3, padx=5)
        self.score_entry = ttk.Entry(add_frame, textvariable=self.score_var, width=10)
        self.score_entry.grid(row=0, column=4, padx=5)
        self.score_entry.bind("<Return>", lambda e: self.add_item())

        ttk.Button(add_frame, text="Add", width=10, command=self.add_item).grid(row=0, column=5, padx=5)
        ttk.Button(add_frame, text="Update", width=10, command=self._open_update_window).grid(row=0, column=6, padx=5)

        # --- remove frame ---
        ttk.Label(remove_frame, text="ID to remove:").grid(row=0, column=0, padx=5)
        remove_entry = ttk.Entry(remove_frame, textvariable=self.remove_id_var, width=10)
        remove_entry.grid(row=0, column=1, padx=5)
        remove_entry.bind("<Return>", lambda e: self.remove_item())
        ttk.Button(remove_frame, text="Remove", width=10, command=self.remove_item).grid(row=0, column=2, padx=5)

        # --- keybindings ---
        self.root.bind("<Control-u>", lambda e: self._open_update_window())
        self.root.bind("<Control-f>", lambda e: search_entry.focus_set())
        self.root.bind("<Control-o>", lambda e: table_entry.focus_set())
        self.root.bind("<Control-n>", lambda e: self.id_entry.focus_set())
        self.root.bind("<Escape>", self.toggle_escape_menu)

        self.id_var.set("")
        self.score_var.set("")
        self.remove_id_var.set("")

    # ---- table selection / rendering ----
    def select_table(self):
        table_suffix = self.table_name.get().strip()
        if not table_suffix:
            messagebox.showwarning("Input Error", "Please fill the Table to present field.")
            return

        if table_suffix.endswith("Students"):
            self.db.courses.create_students_table(self.course_name)
        elif not self.db.courses.table_exists(table_suffix, self.course_name):
            self._ask_base_grade(table_suffix)
            return

        self._render_table(table_suffix)

    def _render_table(self, table_suffix: str):
        full_table = self.course_name + table_suffix
        columns = list(self.db.assessments.get_columns(full_table))
        base_grade = self.db.courses.get_base_grade(self.course_name, table_suffix)

        is_students_table = table_suffix.endswith("Students")
        if not is_students_table:
            lower_cols = [c.lower() for c in columns]
            insert_at = lower_cols.index("comment") if "comment" in lower_cols else len(columns)
            columns.insert(insert_at, "Calculated")

        if not columns:
            messagebox.showinfo("No Columns", f"Table '{table_suffix}' has no columns.")
            return

        raw_rows = self.db.assessments.get_rows(full_table)
        display_rows = []
        if not is_students_table and base_grade:
            score_index = [c.lower() for c in self.db.assessments.get_columns(full_table)].index("score")
            calc_index = columns.index("Calculated")
            for row in raw_rows:
                row_list = list(row)
                calculated = StatsService.calculated_score(row[score_index], base_grade)
                row_list.insert(calc_index, calculated)
                display_rows.append(row_list)
        else:
            display_rows = [list(r) for r in raw_rows]

        self.table_view.render(columns, display_rows, _COLUMN_WIDTHS)
        self._update_stats(table_suffix, full_table, base_grade)

    def _update_stats(self, table_suffix, full_table, base_grade):
        if not ("Problem" in table_suffix or "Quiz" in table_suffix):
            self.stats_label.config(text="")
            return
        columns = self.db.assessments.get_columns(full_table)
        if "Score" not in columns:
            self.stats_label.config(text="")
            return
        scores = self.db.assessments.get_column_values(full_table, "Score")
        stats = StatsService.compute(scores, base_grade)
        self.stats_label.config(text=stats.as_text() if stats else "")

    def _ask_base_grade(self, table_suffix):
        from ui.widgets.popup import Popup

        popup = Popup(self.root, "Base Grade", self.theme, width=250, height=150, custom_titlebar=False)
        popup.content.grid_columnconfigure(0, weight=1)
        ttk.Label(popup.content, text=f"Base grade for {table_suffix}").grid(row=0, column=0)
        entry = ttk.Entry(popup.content, textvariable=self.base_grade_var, width=10)
        entry.grid(row=1, column=0)
        entry.focus_set()

        def submit():
            base = self.base_grade_var.get()
            self.db.courses.create_assessment_table(table_suffix, self.course_name, base)
            popup.destroy()
            self._render_table(table_suffix)

        btn = ttk.Button(popup.content, text="Create Table", command=submit)
        btn.grid(row=2, column=0)
        entry.bind("<Return>", lambda e: btn.invoke())
        popup.center_over_parent()

    # ---- add / remove / update ----
    def _lookup_student_name(self, event=None):
        try:
            sid = str(self.id_var.get()).strip()
        except Exception:
            self.name_lookup_label.config(text="Name: ---")
            return
        if not sid:
            self.name_lookup_label.config(text="Name: ---")
            return
        try:
            name = self.db.students.get_name(int(sid), self.course_name)
        except (ValueError, Exception):
            logger.debug("Name lookup failed for sid=%r", sid, exc_info=True)
            name = None
        if name:
            self.name_lookup_label.config(text=f"Name: {name}")
        elif name == "":
            self.name_lookup_label.config(text="Name: ---")
        else:
            self.name_lookup_label.config(text="Name: Not found")

    def add_item(self):
        sid = self.id_var.get()
        score = self.score_var.get()
        if not sid or not score:
            messagebox.showwarning("Input Error", "Please fill both id and score fields.")
            return

        name = self.db.students.get_name(sid, self.course_name) or f"Sid {sid}"

        def on_comment(comment_text):
            full_table = self.course_name + self.table_name.get()
            self.db.assessments.add_or_replace_item(full_table, sid, score, comment_text)
            self.select_table()
            self.id_entry.focus_set()

        CommentWindow(self.root, self.theme, name, on_comment)
        self.id_var.set("")
        self.score_var.set("")
        self.name_lookup_label.config(text="Name: ---")

    def remove_item(self):
        sid = self.remove_id_var.get()
        if not sid:
            messagebox.showwarning("Input Error", "Please fill id field.")
            return
        full_table = self.course_name + self.table_name.get()
        self.db.assessments.remove_item(full_table, sid)
        self.select_table()
        self.remove_id_var.set("")

    def _open_update_window(self):
        values = self.table_view.get_selected_values() if self.table_view else None
        if not values:
            messagebox.showwarning("Selection Required", "Please select a row to update.")
            return
        sid, score = values[0], values[1]
        comment = values[3] if len(values) > 3 else ""

        def on_save(sid_, new_score, new_comment):
            self.db.assessments.update_item(self.course_name, self.table_name.get(), sid_, new_score, new_comment)
            self.select_table()
            self.table_view.select_row_by_sid(sid_)

        UpdateWindow(self.root, self.theme, sid, score, comment, on_save)

    # ---- export / finalize / histogram ----
    def _export_csv(self):
        if not self.table_view or not self.table_view.tree:
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV files", "*.csv")], title="Save as CSV",
        )
        if not filepath:
            return
        try:
            self.table_view.export_csv(filepath)
            messagebox.showinfo("Success!", "CSV exported successfully!")
        except Exception as e:
            logger.exception("CSV export failed")
            messagebox.showerror("Error", str(e))

    def _export_excel(self):
        if not self.table_view or not self.table_view.tree:
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx", filetypes=[("Excel Workbook", "*.xlsx")], title="Save as Excel",
        )
        if not filepath:
            return
        try:
            self.table_view.export_excel(filepath)
            messagebox.showinfo("Success!", "Excel file exported successfully!")
        except Exception as e:
            logger.exception("Excel export failed")
            messagebox.showerror("Error", str(e))

    def _finalize_course(self):
        if not self.course_name:
            messagebox.showwarning("Input Error", "Please enter a course name.")
            return
        columns, rows = self.db.courses.finalize(self.course_name)
        if not rows:
            messagebox.showinfo("No Data", "No students/scores found to finalize.")
            return
        prefix = self.course_name
        cleaned_columns = [c.removeprefix(prefix) if c.startswith(prefix) else c for c in columns]
        self.table_view.render(cleaned_columns, [list(r) for r in rows], _COLUMN_WIDTHS)
        messagebox.showinfo("Success!", "Course has been finalized!")

    def _show_histogram(self):
        full_table = self.course_name + self.table_name.get()
        try:
            scores = self.db.assessments.get_column_values(full_table, "Score")
        except Exception:
            logger.exception("Could not fetch scores for histogram")
            messagebox.showerror("Error", "Could not load scores for this table.")
            return
        numeric_scores = [s for s in scores if isinstance(s, (int, float))]
        if not numeric_scores:
            messagebox.showinfo("No Data", "No numeric scores to plot.")
            return
        HistogramWindow(self.root, self.theme, numeric_scores)

    # ---- settings / theming ----
    def _open_settings(self):
        self.toggle_escape_menu()

        def on_theme_change(theme_name):
            self.theme.set_theme(theme_name)
            self.theme.apply(self.root)
            self.theme.save_theme(theme_name)

        SettingsWindow(self.root, self.theme, on_theme_change, self._reopen_course_setup)

    # ---- escape menu ----
    def toggle_escape_menu(self, event=None):
        if self.esc_menu_open:
            if self.escape_menu:
                self.escape_menu.destroy()
            self.escape_menu = None
            self.esc_menu_open = False
            return

        menu = Toplevel(self.root)
        self.escape_menu = menu
        menu.columnconfigure(0, weight=1)
        menu.columnconfigure(1, weight=1)
        menu.columnconfigure(2, weight=1)
        menu.overrideredirect(True)
        menu.configure(bg=self.theme.PURPLE, highlightthickness=3,
                        highlightbackground="black", highlightcolor="black")
        menu.attributes("-topmost", True)
        menu.geometry("260x340+0+0")
        self._center_over_root(menu)

        ttk.Label(menu, text="Menu", style="MenuLabel.TLabel").grid(row=0, column=1, pady=5, padx=5, sticky="n")

        close_border = Frame(menu, bg="black", bd=0)
        close_border.grid(row=1, column=1, pady=5, padx=5, sticky="n")
        ttk.Button(close_border, text="Close Application", command=self._confirm_close,
                   style="MenuButtons.TButton").grid(row=0, column=0, pady=2, padx=2)

        settings_border = Frame(menu, bg="black", bd=0)
        settings_border.grid(row=2, column=1, pady=5, padx=5, sticky="n")
        ttk.Button(settings_border, text="Settings", command=self._open_settings,
                   style="MenuButtons.TButton").grid(row=0, column=0, pady=2, padx=2)

        self.esc_menu_open = True

    def _center_over_root(self, window):
        self.root.update_idletasks()
        window.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (window.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (window.winfo_height() // 2)
        window.geometry(f"+{x}+{y}")

    def _confirm_close(self):
        if self.escape_menu:
            self.escape_menu.lower()
        if messagebox.askyesno("Confirm Exit", "Are you sure you want to close the application?"):
            self.on_close()
        elif self.escape_menu:
            self.escape_menu.lift()
