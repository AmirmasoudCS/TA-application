# TA Application

A desktop app for teaching assistants to manage class rosters, track and grade assignments, and export results. Built with Python and Tkinter, backed by SQLite.

## Features

- Manage multiple courses, each with its own students, tables, and grades
- Import class rosters from simple text files
- Add, update, and remove student scores with optional comments
- Auto-calculate grades against a configurable base grade
- Search and sort results in-app
- Export any table to CSV or Excel
- Visualize score distributions with a built-in histogram
- Finalize a course into a single combined grade sheet
- Switch between multiple color themes

## Screenshots

<!-- Add screenshots below. Example: -->
<!-- ![Main window](screenshots/main_window.png) -->

**Main window**

`[screenshot placeholder]`

**Course setup**

`[screenshot placeholder]`

**Settings / themes**

`[screenshot placeholder]`

**Score histogram**

`[screenshot placeholder]`

## Getting Started

### Requirements

- Python 3.9+
- See [`requirements.txt`](requirements.txt) for Python dependencies

### Installation

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
pip install -r requirements.txt
```

### Running

```bash
python main.py
```

On first launch, you'll be asked to enter a course name and select a roster file to import students from.

### Roster files

Roster files live in `data/rosters/` and are plain `.txt` files, one student per line, in the format:

```
Firstname Lastname StudentID
```

## Project Structure

<!-- Paste the tree structure output from your tool here -->

```txt
[project tree placeholder]
```

## Tech Stack

- **Python** / **Tkinter** - UI
- **SQLite** - persistence
- **openpyxl** - Excel export
- **matplotlib** - score histograms

## License

See [LICENSE](LICENSE).