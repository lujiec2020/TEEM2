from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from datascience import Table

DEFAULT_TZ = "America/New_York"


def tiktok_utc_string_to_timestamp(ts_str: str, tz: str = DEFAULT_TZ) -> str:
    """
    Convert TikTok UTC string 'YYYY-MM-DD HH:MM:SS' -> readable local timestamp string.
    Output example: '2026-02-04 02:14:07 PM EST'
    """
    dt_utc = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    dt_local = dt_utc.astimezone(ZoneInfo(tz))
    return dt_local.strftime("%Y-%m-%d %I:%M:%S %p %Z")


def rows_to_table(rows, columns):
    """
    Convert list[dict] -> datascience.Table with consistent columns.
    """
    table = Table()

    if not rows:
        for col in columns:
            table = table.with_column(col, [])
        return table

    for col in columns:
        table = table.with_column(col, [row.get(col, "") for row in rows])

    return table