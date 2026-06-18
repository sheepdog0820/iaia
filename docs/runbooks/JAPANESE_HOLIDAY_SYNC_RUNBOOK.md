# Japanese Holiday Sync Runbook

## Purpose

The calendar uses Japanese public holidays stored in the database. Holiday data is synced from the Cabinet Office CSV and rendered from the local database so calendar display does not depend on an external request.

## Source

- Cabinet Office CSV: https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv
- Override setting: `JAPANESE_HOLIDAY_CSV_URL`

## Automatic Sync

Celery beat runs `schedules.tasks.sync_japanese_holidays` monthly.

- Schedule location: `tableno/settings.py`
- Default timing: first day of every month at 03:20 JST
- Storage model: `schedules.models.JapaneseHoliday`

If the sync fails, existing holiday rows remain in the database and the calendar continues to use the last successful data.
When a sync succeeds, old `cao_csv` rows within the CSV date range that are no longer present in the CSV are removed.

## Manual Sync

Run this after a deployment, after a holiday law update, or when checking a failed scheduled sync.

```bash
python manage.py sync_japanese_holidays
```

To test against another CSV URL:

```bash
python manage.py sync_japanese_holidays --url https://example.test/syukujitsu.csv
```

## Calendar API

The browser reads holidays from:

```text
GET /api/schedules/calendar/holidays/?start=YYYY-MM-DD&end=YYYY-MM-DD
```

The endpoint requires login and returns rows in this shape:

```json
[
  {"date": "2026-01-01", "name": "元日"}
]
```

## Operational Notes

- Do not fetch the Cabinet Office CSV during page rendering.
- Do not delete existing holidays when a sync fails.
- If the Cabinet Office CSV format changes, update `schedules/holiday_sync.py` and run the sync command manually.
- If a one-off holiday is announced and the CSV has not been updated yet, add or correct the row in `JapaneseHoliday` and set `source` to something other than `cao_csv`, for example `manual`. Manual rows are not removed by the CSV sync.
