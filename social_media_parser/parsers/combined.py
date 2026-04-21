"""
Combine Instagram + TikTok event tables into one unified schema.

This module provides:
- A one-call function `social_media_events()` that loads both platforms.
- Helpers for ensuring consistent columns.
- Quick time-based grouping utilities (hour, weekday, date).

All functions are beginner-friendly and designed for use in data science courses.
"""

from datascience import Table
from datetime import datetime

from social_media_parser.parsers.instagram import instagram_events
from src.tiktok_tables.tiktok_events import tiktok_events

FINAL_COLS = ["platform", "object_type", "action_type", "username", "target", "value", "timestamp"]


# ============================================================
# Schema helpers
# ============================================================

def _ensure_column(t: Table, col: str, default=""):
    """
    Ensure a column exists in the table; if missing, create it.

    Parameters
    ----------
    t : Table
        Input datascience Table.
    col : str
        Column name to ensure.
    default : any
        Default value to fill if the column is missing.

    Returns
    -------
    Table
        Table guaranteed to contain the column.
    """
    if col not in t.labels:
        t = t.with_column(col, [default] * t.num_rows)
    return t


def _to_final_schema(t: Table, platform_name: str) -> Table:
    """
    Convert a platform-specific table into the final unified schema.

    Ensures the following columns exist:
    - platform
    - object_type
    - action_type
    - username
    - target
    - value
    - timestamp

    Parameters
    ----------
    t : Table
        Platform-specific event table.
    platform_name : str
        Name of the platform ("instagram" or "tiktok").

    Returns
    -------
    Table
        Table with standardized columns in FINAL_COLS order.
    """
    t = _ensure_column(t, "platform", platform_name)
    t = _ensure_column(t, "username", "")

    for c in ["object_type", "action_type", "target", "value", "timestamp"]:
        t = _ensure_column(t, c, "")

    return t.select(*FINAL_COLS)


# ============================================================
# Main combined parser
# ============================================================

def social_media_events(
    instagram_folder: str,
    tiktok_json: str,
    tz: str = "America/New_York",
    start_date: str | None = None,
    end_date: str | None = None,
) -> Table:
    """
    Load Instagram + TikTok events and return a single combined table.

    This function:
    - Reads an Instagram takeout folder.
    - Reads TikTok's `user_data_tiktok.json`.
    - Applies optional date filtering.
    - Standardizes both into a shared schema.
    - Returns one unified datascience Table.

    Parameters
    ----------
    instagram_folder : str
        Path to the folder containing Instagram JSON export files.
    tiktok_json : str
        Path to TikTok's `user_data_tiktok.json`.
    tz : str
        Timezone for timestamp conversion.
    start_date : str or None
        Optional start date filter (MM-DD-YYYY, YYYY-MM-DD, etc.).
    end_date : str or None
        Optional end date filter.

    Returns
    -------
    Table
        Combined Instagram + TikTok events in a consistent schema.

    Examples
    --------
    >>> combined = social_media_events("data/instagram", "data/user_data_tiktok.json")
    >>> combined.num_rows
    1204
    >>> combined.labels
    ['platform', 'object_type', 'action_type', 'username', 'target', 'value', 'timestamp']
    """
    insta = instagram_events(
        instagram_folder,
        tz=tz,
        start_date=start_date,
        end_date=end_date
    ).table

    tiktok = tiktok_events(
        tiktok_json,
        tz=tz,
        start_date=start_date,
        end_date=end_date
    )

    insta_final = _to_final_schema(insta, "instagram")
    tiktok_final = _to_final_schema(tiktok, "tiktok")

    combined = insta_final.append(tiktok_final)

    # Sort chronologically if possible
    if "timestamp" in combined.labels:
        try:
            combined = combined.sort("timestamp")
        except Exception:
            pass

    return combined


# ============================================================
# Time grouping helpers
# ============================================================

def _parse_timestamp_to_dt(ts: str):
    """
    Convert a timestamp string into a Python datetime object.

    Expected format:
    'YYYY-MM-DD HH:MM:SS AM/PM TZ'

    Parameters
    ----------
    ts : str
        Timestamp string.

    Returns
    -------
    datetime or None
        Parsed datetime, or None if parsing fails.
    """
    if ts is None:
        return None
    ts = str(ts).strip()
    parts = ts.split(" ")
    if len(parts) < 3:
        return None
    ts_no_tz = " ".join(parts[:-1])
    try:
        return datetime.strptime(ts_no_tz, "%Y-%m-%d %I:%M:%S %p")
    except Exception:
        return None


def add_basic_time_columns(t: Table) -> Table:
    """
    Add standard time columns to a combined events table.

    Adds:
    - timestamp_dt
    - hour
    - weekday
    - date

    Parameters
    ----------
    t : Table
        Combined events table.

    Returns
    -------
    Table
        Table with added time columns.
    """
    t = t.with_column("timestamp_dt", t.apply(_parse_timestamp_to_dt, "timestamp"))
    t = t.with_column("hour", t.apply(lambda d: d.hour if d else None, "timestamp_dt"))
    t = t.with_column("weekday", t.apply(lambda d: d.strftime("%A") if d else None, "timestamp_dt"))
    t = t.with_column("date", t.apply(lambda d: d.date() if d else None, "timestamp_dt"))
    return t


def events_by_hour(t: Table) -> Table:
    """
    Group combined events by hour of day.

    Returns
    -------
    Table
        Hour → count table sorted by count descending.
    """
    if "hour" not in t.labels:
        t = add_basic_time_columns(t)
    return t.group("hour").sort("count", descending=True)


def events_by_weekday(t: Table) -> Table:
    """
    Group combined events by weekday.

    Returns
    -------
    Table
        Weekday → count table sorted by count descending.
    """
    if "weekday" not in t.labels:
        t = add_basic_time_columns(t)
    return t.group("weekday").sort("count", descending=True)


def events_by_date(t: Table) -> Table:
    """
    Group combined events by calendar date.

    Returns
    -------
    Table
        Date → count table sorted chronologically.
    """
    if "date" not in t.labels:
        t = add_basic_time_columns(t)
    return t.group("date").sort("date")
