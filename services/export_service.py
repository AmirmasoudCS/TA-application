"""
Handles writing CSV/Excel/PDF exports of grade data.

This replaces two separate, redundant implementations from the old code:
  - services/export_services.py (ExportServices) — used pandas, was never
    actually imported/wired up anywhere.
  - TAapp.py's inline toCSV()/toExcel() functions — used openpyxl, was the
    one actually connected to the UI buttons.

This version keeps the openpyxl dependency (avoids adding pandas just for
this), defaults to config.EXPORT_DIRECTORY, but still lets the caller (UI)
pass an explicit path - or just a different directory - from a file-save
dialog if they want to.

PDF export was added alongside CSV/Excel for the single "Export" popup
(see ui/windows/export_window.py) that lets a TA pick CSV/Excel/PDF/All
in one place instead of separate buttons per format. It uses fpdf2 (a
lightweight PDF library with no heavy dependencies) rather than something
like reportlab, since all we need is a simple bordered table, not a full
document layout engine.
"""
import csv
import os
from datetime import datetime
from typing import List, Optional, Sequence

from openpyxl import Workbook
from fpdf import FPDF

from config import EXPORT_DIRECTORY
from logging_setup import get_logger

logger = get_logger("services.export")


class ExportService:
    def __init__(self, export_directory: str = EXPORT_DIRECTORY):
        self.export_directory = export_directory
        os.makedirs(self.export_directory, exist_ok=True)

    def default_filename(self, base_name: str, extension: str, directory: Optional[str] = None) -> str:
        """directory overrides self.export_directory for one call - used
        when the user has browsed to a different save location than the
        app's default (see ExportWindow)."""
        target_directory = directory or self.export_directory
        os.makedirs(target_directory, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        clean_name = base_name.replace(" ", "_")
        return os.path.join(target_directory, f"{clean_name}_{timestamp}.{extension}")

    def export_to_csv(self, columns: Sequence[str], rows: Sequence[Sequence], filepath: str = None,
                       base_name: str = "export", directory: Optional[str] = None) -> str:
        filepath = filepath or self.default_filename(base_name, "csv", directory=directory)
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL, delimiter=";")
            writer.writerow(columns)
            writer.writerows(rows)
        logger.info("Exported CSV to %s (%d rows)", filepath, len(rows))
        return filepath

    def export_to_excel(self, columns: Sequence[str], rows: Sequence[Sequence], filepath: str = None,
                         base_name: str = "export", directory: Optional[str] = None) -> str:
        filepath = filepath or self.default_filename(base_name, "xlsx", directory=directory)
        wb = Workbook()
        ws = wb.active
        ws.append(list(columns))
        for row in rows:
            ws.append(list(row))
        wb.save(filepath)
        logger.info("Exported Excel to %s (%d rows)", filepath, len(rows))
        return filepath

    def export_to_pdf(self, columns: Sequence[str], rows: Sequence[Sequence], filepath: str = None,
                       base_name: str = "export", directory: Optional[str] = None, title: Optional[str] = None) -> str:
        """Renders a simple bordered table - one page, landscape, columns
        sized evenly across the page width. Cells that are too long for
        their column are truncated with '...' rather than wrapped, since
        wrapping a table cell in fpdf2 complicates row alignment for
        comparatively little benefit at this table size.

        fpdf2's built-in "Helvetica" is a core PDF font limited to Latin-1
        (it has no way to render, say, Turkish, Vietnamese, Cyrillic, or
        Chinese/Arabic characters, or several "smart" punctuation marks
        outside that range) - without a Unicode-capable embedded TTF font,
        which this app doesn't currently bundle, any such character would
        crash pdf.output() with a UnicodeEncodeError. Every piece of text
        is sanitized through _safe_pdf_text() first: anything outside
        Latin-1 is replaced with '?' so the export always succeeds, at the
        cost of not rendering non-Latin-1 names/comments correctly. If
        precise rendering of those names matters, the real fix is
        bundling a Unicode TTF (e.g. DejaVu Sans) and loading it via
        pdf.add_font() instead of the core Helvetica font.
        """
        filepath = filepath or self.default_filename(base_name, "pdf", directory=directory)

        pdf = FPDF(orientation="L", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=True, margin=10)
        pdf.add_page()

        if title:
            pdf.set_font("Helvetica", style="B", size=14)
            pdf.cell(0, 10, self._safe_pdf_text(title), ln=1, align="C")

        usable_width = pdf.w - pdf.l_margin - pdf.r_margin
        col_count = max(len(columns), 1)
        col_width = usable_width / col_count

        pdf.set_font("Helvetica", style="B", size=9)
        for col in columns:
            text = self._safe_pdf_text(str(col))
            pdf.cell(col_width, 8, self._fit_text(pdf, text, col_width), border=1)
        pdf.ln()

        pdf.set_font("Helvetica", size=8)
        for row in rows:
            for value in row:
                text = self._safe_pdf_text("" if value is None else str(value))
                pdf.cell(col_width, 7, self._fit_text(pdf, text, col_width), border=1)
            pdf.ln()

        pdf.output(filepath)
        logger.info("Exported PDF to %s (%d rows)", filepath, len(rows))
        return filepath

    @staticmethod
    def _safe_pdf_text(text: str) -> str:
        """Replaces any character the core PDF font can't encode (i.e.
        anything outside Latin-1) with '?', so export_to_pdf never crashes
        on names/comments containing broader Unicode."""
        try:
            text.encode("latin-1")
            return text
        except UnicodeEncodeError:
            return text.encode("latin-1", "replace").decode("latin-1")

    @staticmethod
    def _fit_text(pdf: FPDF, text: str, width: float) -> str:
        max_width = width - 2  # small padding so text doesn't touch the cell border
        if pdf.get_string_width(text) <= max_width:
            return text
        while text and pdf.get_string_width(text + "...") > max_width:
            text = text[:-1]
        return f"{text}..." if text else ""