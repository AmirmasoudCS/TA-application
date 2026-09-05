"""
Handles writing CSV/Excel exports of grade data.

This replaces two separate, redundant implementations from the old code:
  - services/export_services.py (ExportServices) — used pandas, was never
    actually imported/wired up anywhere.
  - TAapp.py's inline toCSV()/toExcel() functions — used openpyxl, was the
    one actually connected to the UI buttons.

This version keeps the openpyxl dependency (avoids adding pandas just for
this), defaults to config.EXPORT_DIRECTORY, but still lets the caller (UI)
pass an explicit path from a file-save dialog if they want to.
"""
import csv
import os
from datetime import datetime
from typing import List, Sequence

from openpyxl import Workbook

from config import EXPORT_DIRECTORY
from logging_setup import get_logger

logger = get_logger("services.export")


class ExportService:
    def __init__(self, export_directory: str = EXPORT_DIRECTORY):
        self.export_directory = export_directory
        os.makedirs(self.export_directory, exist_ok=True)

    def default_filename(self, base_name: str, extension: str) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        clean_name = base_name.replace(" ", "_")
        return os.path.join(self.export_directory, f"{clean_name}_{timestamp}.{extension}")

    def export_to_csv(self, columns: Sequence[str], rows: Sequence[Sequence], filepath: str = None, base_name: str = "export") -> str:
        filepath = filepath or self.default_filename(base_name, "csv")
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL, delimiter=";")
            writer.writerow(columns)
            writer.writerows(rows)
        logger.info("Exported CSV to %s (%d rows)", filepath, len(rows))
        return filepath

    def export_to_excel(self, columns: Sequence[str], rows: Sequence[Sequence], filepath: str = None, base_name: str = "export") -> str:
        filepath = filepath or self.default_filename(base_name, "xlsx")
        wb = Workbook()
        ws = wb.active
        ws.append(list(columns))
        for row in rows:
            ws.append(list(row))
        wb.save(filepath)
        logger.info("Exported Excel to %s (%d rows)", filepath, len(rows))
        return filepath
