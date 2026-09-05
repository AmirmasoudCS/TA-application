"""
Score-distribution histogram popup, extracted from TAapp.py's
showHistogram(). Takes an already-fetched list of numeric scores rather
than reaching into the database itself, so it stays a pure display widget.
"""
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ui.widgets.popup import Popup


class HistogramWindow(Popup):
    def __init__(self, parent, theme, scores, bins: int = 10):
        super().__init__(parent, "Score Histogram", theme, width=800, height=550,
                          custom_titlebar=True, modal=False)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        fig, ax = plt.subplots()
        fig.patch.set_facecolor(theme.BG)
        ax.set_facecolor(theme.CARD)
        ax.hist(scores, bins=bins, edgecolor=theme.BORDER, color=theme.PURPLE)
        ax.set_title("Score Distribution", color=theme.FG)
        ax.set_xlabel("Scores", color=theme.FG)
        ax.set_ylabel("Number of Students", color=theme.FG)
        ax.grid(color=theme.BORDER, linestyle="--", alpha=0.3)
        ax.tick_params(colors=theme.FG)
        for spine in ax.spines.values():
            spine.set_color(theme.BORDER)

        canvas = FigureCanvasTkAgg(fig, master=self.content)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.center_over_parent()

    def close(self):
        plt.close("all")
        super().close()