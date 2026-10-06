"""Shared Google Sheets export schema and range defaults."""

import re
from urllib.parse import quote

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
SHEETS_ID_ERROR_MESSAGE = "出力先のスプレッドシートIDを正しく指定してください。"


def sheet_export_character_ids(payload, values):
    """Resolve an exact export selection, never interpret unknown targets as all."""
    if not isinstance(payload, dict) or payload.get("selection_snapshot") is not True:
        return None
    selected = payload.get("character_ids")
    if not isinstance(selected, list) or any(type(pk) is not int or not 0 < pk < 2**63 for pk in selected):
        return None
    if len(set(selected)) != len(selected):
        return None
    if not isinstance(values, list) or not values or values[0] != SHEET_COLUMNS:
        return None
    rows = values[1:]
    if any(not isinstance(row, list) or len(row) != len(SHEET_COLUMNS) for row in rows):
        return None
    row_ids = [row[0] for row in rows]
    if any(type(pk) is not int for pk in row_ids) or row_ids != selected:
        return None
    return selected


_A1_START_CELL_PATTERN = re.compile(r"^\$?([A-Za-z]+)\$?([1-9]\d*)$")


def normalize_spreadsheet_id(value):
    """Validate an opaque ID without inventing Google's allowed-character grammar."""
    if not isinstance(value, str):
        raise ValueError(SHEETS_ID_ERROR_MESSAGE)
    value = value.strip()
    if not value or value in {".", ".."} or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError(SHEETS_ID_ERROR_MESSAGE)
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise ValueError(SHEETS_ID_ERROR_MESSAGE) from None
    return value


def sheet_values_update_url(spreadsheet_id, start_range):
    """Keep each validated destination in a single URL path component."""
    sheet_id = quote(normalize_spreadsheet_id(spreadsheet_id), safe="")
    range_name = quote(normalize_sheet_start_range(start_range), safe="")
    return f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{range_name}"


def normalize_sheet_start_range(value):
    """Return a normalized A1 start cell while preserving an optional sheet prefix."""
    text = str(value).strip()
    try:
        text.encode("utf-8")
    except UnicodeError:
        raise ValueError(SHEETS_RANGE_ERROR_MESSAGE) from None
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
