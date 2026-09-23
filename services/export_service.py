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
import glob
import os
from datetime import datetime
from typing import List, Optional, Sequence, Tuple

from openpyxl import Workbook
from fpdf import FPDF

from config import EXPORT_DIRECTORY, FONTS_DIRECTORY
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
        # utf-8-sig (UTF-8 with a BOM) rather than plain utf-8: Excel does
        # not reliably auto-detect a BOM-less UTF-8 CSV, especially on a
        # Windows machine whose locale isn't UTF-8, and instead guesses the
        # system codepage - which turns anything outside ASCII (e.g.
        # Persian names) into mojibake even though the file itself was
        # written correctly. The BOM lets Excel detect UTF-8 reliably; a
        # BOM-aware reader treats it as a zero-width marker, not data.
        with open(filepath, mode="w", newline="", encoding="utf-8-sig") as f:
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

        Font handling: fpdf2's built-in "Helvetica" is a core PDF font
        limited to Latin-1 - it can't render Persian, Arabic, Chinese,
        Cyrillic, etc. _configure_pdf_font() checks config.FONTS_DIRECTORY
        for a TA-provided .ttf and, if one is found, loads it and uses it
        for the whole table instead. If none is found, this falls back to
        the core font with non-Latin-1 characters replaced by '?', same as
        before. See _configure_pdf_font()'s docstring for what a bundled
        font does and doesn't fix on its own (particularly for
        right-to-left, letter-joining scripts like Persian/Arabic).
        """
        filepath = filepath or self.default_filename(base_name, "pdf", directory=directory)

        pdf = FPDF(orientation="L", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=True, margin=10)
        pdf.add_page()

        font_family, supports_bold = self._configure_pdf_font(pdf)
        needs_latin1_fallback = font_family == "Helvetica"

        def clean(value) -> str:
            text = "" if value is None else str(value)
            return self._safe_pdf_text(text) if needs_latin1_fallback else text

        if title:
            pdf.set_font(font_family, style="B" if supports_bold else "", size=14)
            pdf.cell(0, 10, clean(title), ln=1, align="C")

        usable_width = pdf.w - pdf.l_margin - pdf.r_margin
        col_count = max(len(columns), 1)
        col_width = usable_width / col_count

        pdf.set_font(font_family, style="B" if supports_bold else "", size=9)
        for col in columns:
            pdf.cell(col_width, 8, self._fit_text(pdf, clean(col), col_width), border=1)
        pdf.ln()

        pdf.set_font(font_family, size=8)
        for row in rows:
            for value in row:
                pdf.cell(col_width, 7, self._fit_text(pdf, clean(value), col_width), border=1)
            pdf.ln()

        pdf.output(filepath)
        logger.info("Exported PDF to %s (%d rows, font=%s)", filepath, len(rows), font_family)
        return filepath

    @staticmethod
    def _configure_pdf_font(pdf: FPDF) -> Tuple[str, bool]:
        """Looks for a .ttf file in config.FONTS_DIRECTORY and, if found,
        registers it as a custom font ("ExportUnicode") for this PDF.
        Returns (font_family, supports_bold) - supports_bold is only True
        for the built-in "Helvetica", since a single auto-detected .ttf
        only provides one style (fpdf2 needs a separate bold .ttf added
        explicitly for a real bold face, which this simple auto-detection
        doesn't attempt).

        This fixes '?' showing up for scripts the core font can't render
        at all (e.g. Persian/Arabic, Cyrillic, CJK) as long as the chosen
        .ttf includes those glyphs. It does NOT by itself guarantee
        correct-looking right-to-left or letter-joining scripts (Persian,
        Arabic, Hebrew): that needs "text shaping", which fpdf2 supports
        via pdf.set_text_shaping(True) but requires the optional
        `uharfbuzz` package (`pip install "fpdf2[text-shaping]"`). This
        method tries to enable it and logs a warning (once) if it's not
        available, rather than failing the export - the font will still
        render, just possibly with disconnected letters or in the wrong
        visual order until that package is installed.
        """
        fonts = sorted(glob.glob(os.path.join(FONTS_DIRECTORY, "*.ttf")))
        if not fonts:
            return "Helvetica", True

        font_path = fonts[0]
        try:
            pdf.add_font("ExportUnicode", fname=font_path)
        except Exception:
            logger.exception(
                "Failed to load PDF font %s, falling back to the built-in font "
                "(non-Latin-1 text will show as '?')", font_path,
            )
            return "Helvetica", True

        try:
            pdf.set_text_shaping(True)
        except Exception:
            logger.warning(
                "Loaded PDF font %s but text shaping isn't available - install it with "
                "`pip install \"fpdf2[text-shaping]\"` for correct rendering of "
                "right-to-left / letter-joining scripts like Persian or Arabic. "
                "Without it, glyphs will render but may look disconnected or "
                "appear in the wrong order.", font_path,
            )
        return "ExportUnicode", False

    @staticmethod
    def _safe_pdf_text(text: str) -> str:
        """Replaces any character the core PDF font can't encode (i.e.
        anything outside Latin-1) with '?'. Only used as a fallback when
        no custom Unicode font was found by _configure_pdf_font()."""
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