"""Shared Google Sheets export schema and range defaults."""

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
