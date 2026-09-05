# TA Application — Refactor Notes

## What changed structurally

Old (single-file-ish):
```
config.py, TAapp.py, teacherAssistantAppDB.py, configure_styles.py,
services/export_services.py (unused)
```

New (modular, OOP):
```
main.py                      # entry point
config.py                    # portable paths (fixed hardcoded C:\ path)
logging_setup.py             # logs/ instead of silent failures

db/
  connection.py               # sqlite3 wrapper
  models.py                   # Student, ScoreEntry, AssessmentInfo dataclasses
  course_repository.py        # course/assessment table lifecycle, finalize
  student_repository.py       # roster CRUD
  assessment_repository.py    # score CRUD, generic table reads
  database.py                 # composition root (Database class)

services/
  roster_import_service.py    # reads data/rosters/*.txt  <- THE FIX
  export_service.py           # writes CSV/Excel to data/exports/
  stats_service.py            # grade stats + score->calculated conversion

ui/
  theme.py                    # ported configure_styles.py, path bug fixed
  main_window.py              # MainWindow controller (replaces all TAapp.py globals)
  widgets/
    popup.py                  # reusable modal base class
    table_view.py             # Treeview wrapper: sort/filter/export
  windows/
    course_setup_window.py    # course name + roster picker
    comment_window.py
    update_window.py
    histogram_window.py
    settings_window.py
```

## The export/roster bug — what was actually wrong, and the fix

The `.txt` files under the old `exports/` directory were never exports —
they were **class rosters** consumed at course setup to populate the
Students table. `Database.populateStudents()` read them using a
hardcoded, wrong `database_directory` path unrelated to `config.py`.

Fixed by:
- Splitting the concept in two, with two directories:
  `config.ROSTER_DIRECTORY` (`data/rosters/`, input) and
  `config.EXPORT_DIRECTORY` (`data/exports/`, output).
- `services/roster_import_service.py` owns all roster file reading/parsing.
  `services/export_service.py` owns all CSV/Excel writing. They no longer
  share a directory or a code path.
- `ui/windows/course_setup_window.py` now lists actual files found in
  `data/rosters/` via a dropdown instead of asking you to blind-type a
  filename.

**Action needed from you:** move your existing roster `.txt` file(s)
(e.g. the old `exports/DSA4042s.txt`) into `data/rosters/` in the new
project. Copy your existing `universityDB.db` into the project root
(next to `main.py`) — same filename, same location as before.

## Other bugs fixed along the way

- `Database.__init__` hardcoded `C:\Users\Hamegani ost\...` — removed;
  uses the path passed in from `config.DB_PATH`.
- `removeItem` built SQL with the id inlined directly in the string
  instead of as a bound parameter — fixed.
- `finalizeTable`: had a typo (`VALUSE` instead of `VALUES`, so it always
  threw) and rebuilt/re-ran `CREATE TABLE` inside a loop. Rewritten as
  `CourseRepository.finalize_into_table()`.
- `getColumnValues`-equivalent (`AssessmentRepository.get_column_values`)
  now correctly double-quotes the column identifier — an earlier draft of
  this refactor briefly introduced a regression here (single-quoted column
  names are string literals in SQLite, not identifiers) and it was caught
  by the smoke tests before shipping.
- `configure_styles.py`'s theme save/load used a hardcoded, Windows-style
  relative path (`"settings\\theme_config.txt"`) — now uses
  `config.THEME_CONFIG_PATH` (absolute, portable).
- Bare/broad `except: ...: pass` blocks throughout the original UI code
  are replaced with logging via `logging_setup.get_logger(...)`, writing
  to `logs/taapp.log`.
- The dead, unused `services/export_services.py` (pandas-based, never
  imported anywhere) and the live-but-duplicated `toCSV`/`toExcel` in
  `TAapp.py` (openpyxl-based) are merged into one
  `services/export_service.py`.

## What's intentionally different (design decisions, not bugs)

- All the module-level globals in `TAapp.py` (`main_window`, `tableView`,
  `course_window`, `escMenuIsOpen`, `sortStates`, etc.) are now instance
  attributes on `ui.main_window.MainWindow`.
- Popup windows no longer read the database directly — `MainWindow` (the
  controller) queries the DB and passes plain data + a callback into each
  popup. This keeps popups reusable/testable without a live DB connection.
- `TableView` doesn't query the database either — it only renders rows it's
  given and filters/sorts/exports the data it's already holding.
- `Courses/` directory from the original tree was unused/dead — dropped
  from the new structure. If you want per-course export subfolders, that'd
  now be a small addition to `ExportService`.

## Testing status

This refactor was built and unit-tested in a sandbox **without a display
or tkinter installed** — the `db/` and `services/` layers were exercised
directly with real sqlite3 (all passing), and the `ui/` layer was verified
for syntax correctness and import-time wiring only (via a stubbed
`tkinter`/`matplotlib`), not click-tested.

**Before relying on this, please do a manual pass through:**
1. Launching `main.py`, course setup, roster import
2. Add / update / remove a score, with comment
3. Search/filter, sort columns
4. Export to CSV and Excel
5. Finalize course
6. Histogram popup
7. Settings: theme switching, "Apply New Course"
8. Esc menu open/close, Ctrl+U / Ctrl+F / Ctrl+O / Ctrl+N shortcuts

If anything breaks, check `logs/taapp.log` first — that's the new
source of truth instead of silently-swallowed exceptions.
