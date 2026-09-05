# TA Application

A desktop app for teaching assistants to manage class rosters, track and grade assignments, and export results. Built with Python and Tkinter, backed by SQLite.

## ✨ Features

- **Course & roster management**: Create multiple courses and import student rosters from text files.
- **Grading**: Add, update, and remove scores, with optional comments and automatic grade calculation.
- **Results**: Search and sort tables, visualize score distributions, and export results to CSV or Excel.
- **Course finalization**: Combine assessment tables into a single grade sheet.
- **Customization**: Switch between multiple color themes.

## 🖼️ Screenshots

### Main window

<div align="center">

<img src="assets/screenshots/main_window.png">

<em><p>Browse tables, search students, manage scores, and export or finalize a course.</p></em>

</div>

### Course setup

<table align="center">
  <tr>
    <td align="center">
      <img src="assets/screenshots/enter_course.png"><br>
      <em>Enter a course name.</em>
    </td>
    <td align="center">
      <img src="assets/screenshots/select_rouster.png"><br>
      <em>Select a roster file to import students.</em>
    </td>
  </tr>
</table>

### Settings / themes

<div align="center">

<img src="assets/screenshots/settings_menu.png">

<em><p>Change the active course and switch color themes.</p></em>

</div>

### Escape menu

<div align="center">

<img src="assets/screenshots/esc_menu.png">

<em><p>Press <code>Esc</code> to quickly access Settings or exit the application.</p></em>

</div>

### Score histogram

<div align="center">

<img src="assets/screenshots/histogram.png">

<em><p>Visualize the score distribution for the selected table.</p></em>

</div>

### Finalize course

<div align="center">

<img src="assets/screenshots/finalize.png">

<em><p>Combine all assessment tables into a single grade sheet. Names are blacked out for privacy.</p></em>

</div>

## 🚀 Getting Started

### Requirements

Python 3.9+ is required. Python dependencies are listed in [`requirements.txt`](requirements.txt).

### Installation

```bash
git clone https://github.com/AmirmasoudCS/TA-application.git
cd TA-application
pip install -r requirements.txt
````

### Running

```bash
python main.py
```

On first launch, enter a course name and select a roster file to import students.

### Roster files

Roster files are stored in `data/rosters/` as plain `.txt` files, with one student per line:

```text
Firstname Lastname StudentID
```

## 📁 Project Structure

```text
📁
├── 📁 assets
│   └── 📁 screenshots
├── 📁 data
│   └── 📁 rosters
├── 📁 db
│   ├── 🐍 __init__.py
│   ├── 🐍 assessment_repository.py
│   ├── 🐍 connection.py
│   ├── 🐍 course_repository.py
│   ├── 🐍 database.py
│   ├── 🐍 models.py
│   └── 🐍 student_repository.py
├── 📁 logs
├── 📁 services
│   ├── 🐍 __init__.py
│   ├── 🐍 export_service.py
│   ├── 🐍 roster_import_service.py
│   └── 🐍 stats_service.py
├── 📁 settings
│   └── 📝 theme_config.txt
├── 📁 ui
│   ├── 📁 widgets
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 popup.py
│   │   └── 🐍 table_view.py
│   ├── 📁 windows
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 comment_window.py
│   │   ├── 🐍 course_setup_window.py
│   │   ├── 🐍 histogram_window.py
│   │   ├── 🐍 settings_window.py
│   │   └── 🐍 update_window.py
│   ├── 🐍 __init__.py
│   ├── 🐍 main_window.py
│   └── 🐍 theme.py
├── 🐍 config.py
├── ⚖️ LICENSE
├── 🐍 logging_setup.py
├── 🐍 main.py
├── 📘 README.md
└── 📝 requirements.txt
```

> Generated using [Tree Printer](https://github.com/AmirmasoudCS/Tree-Printer.git).

## 🛠️ Tech Stack

| Technology           | Purpose          |
| -------------------- | ---------------- |
| **Python / Tkinter** | Desktop UI       |
| **SQLite**           | Data persistence |
| **openpyxl**         | Excel export     |
| **matplotlib**       | Score histograms |

## ⚖️ License

See [LICENSE](LICENSE).
