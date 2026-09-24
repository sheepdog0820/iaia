"""Shared Google Sheets export schema and range defaults."""

import re

SHEET_COLUMNS = [
    "id",
    "name",
    "edition",
    "age",
    "occupation",
    "STR",
    "CON",
    "POW",
    "DEX",
    "APP",
    "SIZ",
    "INT",
    "EDU",
    "HP",
    "MP",
    "SAN",
    "LUCK",
]


def _spreadsheet_column_label(column_number):
    if column_number < 1:
        raise ValueError("column_number must be positive")
    label = ""
    while column_number:
        column_number, remainder = divmod(column_number - 1, 26)
        label = chr(ord("A") + remainder) + label
    return label


SHEETS_DEFAULT_DISPLAY_RANGE = f"Characters!A:{_spreadsheet_column_label(len(SHEET_COLUMNS))}"
SHEETS_DEFAULT_START_RANGE = "Characters!A1"
SHEETS_EXPORT_CHUNK_ROWS = 100
SHEETS_RANGE_ERROR_MESSAGE = "出力範囲はA1形式で指定してください（例: Characters!A1）。"

_A1_START_CELL_PATTERN = re.compile(r"^\$?([A-Za-z]+)\$?([1-9]\d*)$")


def normalize_sheet_start_range(value):
    """Return a normalized A1 start cell while preserving an optional sheet prefix."""
    text = str(value).strip()
    sheet_prefix = ""
    cell_range = text
    if "!" in text:
        sheet_name, cell_range = text.rsplit("!", 1)
        if not sheet_name:
            raise ValueError(SHEETS_RANGE_ERROR_MESSAGE)
        sheet_prefix = f"{sheet_name}!"
    start_cell = cell_range.split(":", 1)[0]
    match = _A1_START_CELL_PATTERN.fullmatch(start_cell)
    if not match:
        raise ValueError(SHEETS_RANGE_ERROR_MESSAGE)
    column, row = match.groups()
    return f"{sheet_prefix}{column.upper()}{int(row)}"


def offset_sheet_start_range(value, row_offset):
    """Offset the row component of an A1 start cell by ``row_offset``."""
    if row_offset < 0:
        raise ValueError("row_offset must not be negative")
    start_range = normalize_sheet_start_range(value)
    sheet_prefix = ""
    start_cell = start_range
    if "!" in start_range:
        sheet_name, start_cell = start_range.rsplit("!", 1)
        sheet_prefix = f"{sheet_name}!"
    match = _A1_START_CELL_PATTERN.fullmatch(start_cell)
    column, row = match.groups()
    return f"{sheet_prefix}{column}{int(row) + row_offset}"
