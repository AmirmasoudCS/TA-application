"""
Entry point for the TA Application.

Replaces the `if __name__ == "__main__":` block at the bottom of the old
TAapp.py. All actual construction now lives in ui.main_window.MainWindow.
"""
from ui.main_window import MainWindow


def main():
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()
