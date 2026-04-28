"""
social_media_parser.py

Utilities for parsing and analyzing Instagram and TikTok data exports.

This module provides:
- Parsing functions for Instagram and TikTok JSON data
- Timezone normalization and timestamp formatting
- Filtering by date ranges
- Analytical helpers for usage patterns (e.g., late-night activity, binge behavior)

All outputs are returned as `datascience.Table` objects.
"""

import json
from pathlib import Path
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

from datascience import Table


# ============================================================
# Beginner-friendly errors
# ============================================================

class StudentInputError(Exception):
    """
    Custom exception for user-facing input errors.

    This is used to provide clear, beginner-friendly error messages
    for invalid paths, dates, or malformed inputs.
    """
    pass


def _raise(msg: str):
    """
    Raise a formatted StudentInputError.

    Args:
        msg (str): Error message to display.

    Raises:
        StudentInputError: Always raised with a warning prefix.
    """
    raise StudentInputError("⚠️ " + msg)


# ============================================================
# Date parsing + range filtering
# ============================================================

def parse_user_date(s: str) -> date:
    """
    Parse a user-provided date string into a `datetime.date`.

    Supported formats:
        - "MM-DD-YYYY"
        - "YYYY-MM-DD"
        - "MM/DD/YYYY"

    Args:
        s (str): Input date string.

    Returns:
        date: Parsed date object.

    Raises:
        StudentInputError: If format is invalid.
    """
    if s is None:
        return None
    s = str(s).strip()
    fmts = ["%m-%d-%Y", "%Y-%m-%d", "%m/%d/%Y"]
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    _raise("Invalid date format.")


def filter_by_date_range(t: Table, start_date=None, end_date=None) -> Table:
    """
    Filter a table to an inclusive date range.

    Uses `timestamp_dt` if available, otherwise attempts to parse
    the `timestamp` column.

    Args:
        t (Table): Input table.
        start_date (str | date, optional): Start date.
        end_date (str | date, optional): End date.

    Returns:
        Table: Filtered table.

    Raises:
        StudentInputError: If end_date < start_date.
    """
    if start_date is None and end_date is None:
        return t

    start_d = parse_user_date(start_date) if not isinstance(start_date, date) else start_date
    end_d = parse_user_date(end_date) if not isinstance(end_date, date) else end_date

    if start_d and end_d and end_d < start_d:
        _raise("end_date must be after start_date.")

    if "timestamp_dt" in t.labels:
        if "date" not in t.labels:
            t = t.with_column("date", t.apply(lambda d: d.date() if d else None, "timestamp_dt"))
    else:
        if "timestamp" not in t.labels:
            return t

        def _try_dt(ts):
            """
            Attempt to parse a timestamp string into a datetime.

            Args:
                ts (str): Timestamp string.

            Returns:
                datetime | None: Parsed datetime or None if invalid.
            """
            if ts is None:
                return None
            parts = str(ts).split(" ")
            ts_no_tz = " ".join(parts[:-1])
            try:
                return datetime.strptime(ts_no_tz, "%Y-%m-%d %I:%M:%S %p")
            except Exception:
                return None

        t = t.with_column("timestamp_dt", t.apply(_try_dt, "timestamp"))
        t = t.with_column("date", t.apply(lambda d: d.date() if d else None, "timestamp_dt"))

    if start_d:
        t = t.where("date", lambda d: d is not None and d >= start_d)
    if end_d:
        t = t.where("date", lambda d: d is not None and d <= end_d)

    return t


# ============================================================
# Table helpers
# ============================================================

def rows_to_table(rows, columns=None) -> Table:
    """
    Convert a list of dictionaries into a `datascience.Table`.

    Args:
        rows (list[dict]): List of row dictionaries.
        columns (list[str], optional): Explicit column order.

    Returns:
        Table: Constructed table with consistent columns.
    """
    if rows is None:
        rows = []
    if columns is None:
        cols = set()
        for r in rows:
            cols |= set(r.keys())
        columns = sorted(cols)

    data = []
    for c in columns:
        data.append(c)
        data.append([r.get(c, "") for r in rows])

    return Table().with_columns(*data)


# ============================================================
# Instagram helpers
# ============================================================

def unix_to_local_dt(unix_ts: int, tz: str) -> datetime:
    """
    Convert a Unix timestamp to a timezone-aware datetime.

    Args:
        unix_ts (int): Unix timestamp.
        tz (str): Timezone string.

    Returns:
        datetime: Localized datetime.
    """
    return datetime.fromtimestamp(int(unix_ts), tz=ZoneInfo(tz))


def format_timestamp(dt_local: datetime) -> str:
    """
    Format a datetime into a readable timestamp string.

    Args:
        dt_local (datetime): Local datetime.

    Returns:
        str: Formatted timestamp string.
    """
    return dt_local.strftime("%Y-%m-%d %I:%M:%S %p %Z")


class EventTable:
    """
    Wrapper class for compatibility with older code.

    Attributes:
        table (Table): Underlying datascience table.
    """
    def __init__(self, table: Table):
        """
        Initialize the wrapper.

        Args:
            table (Table): Table to wrap.
        """
        self.table = table


# ============================================================
# Instagram parser
# ============================================================

def parse_metadata(path: str = "data/instagram_data", tz: str = "America/New_York",
                   start_date=None, end_date=None) -> Table:
    """
    Parse Instagram export data into a unified events table.

    Args:
        path (str): Path to Instagram data folder.
        tz (str): Target timezone.
        start_date (str | date, optional): Filter start date.
        end_date (str | date, optional): Filter end date.

    Returns:
        Table: Parsed Instagram events.

    Raises:
        StudentInputError: If folder does not exist.
    """
    folder = Path(path)

    if not folder.exists() or not folder.is_dir():
        _raise(f"Instagram folder not found: {folder}")

    rows = []
    json_files = sorted(folder.rglob("*.json"))
    if not json_files:
        return Table().with_columns()

    for fp in json_files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        if isinstance(data, dict):
            if "story_activities_story_likes" in data:
                for item in data.get("story_activities_story_likes", []):
                    for entry in item.get("string_list_data", []):
                        unix_ts = entry.get("timestamp")
                        if unix_ts:
                            dt_local = unix_to_local_dt(unix_ts, tz)
                            rows.append({
                                "object_type": "story",
                                "action_type": "like",
                                "username": item.get("title", ""),
                                "target": "",
                                "value": "",
                                "timestamp_dt": dt_local,
                                "timestamp": format_timestamp(dt_local),
                                "timestamp_unix": unix_ts,
                            })

    base = rows_to_table(rows)
    return filter_by_date_range(base, start_date, end_date)


# ============================================================
# TikTok helpers
# ============================================================

def tiktok_utc_string_to_timestamp(ts_str: str, tz: str) -> str:
    """
    Convert a TikTok UTC timestamp string to a localized formatted string.

    Args:
        ts_str (str): UTC timestamp string ("YYYY-MM-DD HH:MM:SS").
        tz (str): Target timezone.

    Returns:
        str: Localized formatted timestamp.
    """
    dt_utc = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo("UTC"))
    dt_local = dt_utc.astimezone(ZoneInfo(tz))
    return dt_local.strftime("%Y-%m-%d %I:%M:%S %p %Z")


def add_basic_time_columns(t: Table) -> Table:
    """
    Add derived time columns to a table.

    Adds:
        - timestamp_dt
        - hour
        - weekday
        - date

    Args:
        t (Table): Input table.

    Returns:
        Table: Table with additional columns.
    """
    def to_dt(ts):
        """
        Convert timestamp string to datetime.

        Args:
            ts (str): Timestamp string.

        Returns:
            datetime | None: Parsed datetime or None.
        """
        if ts is None:
            return None
        ts_no_tz = " ".join(str(ts).split(" ")[:-1])
        try:
            return datetime.strptime(ts_no_tz, "%Y-%m-%d %I:%M:%S %p")
        except Exception:
            return None

    if "timestamp_dt" not in t.labels:
        t = t.with_column("timestamp_dt", t.apply(to_dt, "timestamp"))

    if "hour" not in t.labels:
        t = t.with_column("hour", t.apply(lambda d: d.hour if d else None, "timestamp_dt"))

    if "weekday" not in t.labels:
        t = t.with_column("weekday", t.apply(lambda d: d.strftime("%A") if d else None, "timestamp_dt"))

    if "date" not in t.labels:
        t = t.with_column("date", t.apply(lambda d: d.date() if d else None, "timestamp_dt"))

    return t


# ============================================================
# TikTok parser
# ============================================================

def tiktok_events(json_path: str = "data/tiktok_data/user_data_tiktok.json",
                 tz: str = "America/New_York",
                 start_date=None, end_date=None) -> Table:
    """
    Parse TikTok user data into a structured events table.

    Args:
        json_path (str): Path to TikTok JSON file.
        tz (str): Target timezone.
        start_date (str | date, optional): Filter start date.
        end_date (str | date, optional): Filter end date.

    Returns:
        Table: Parsed TikTok events.

    Raises:
        StudentInputError: If file is not found.
    """
    path = Path(json_path)
    if not path.exists():
        _raise(f"TikTok file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []
    username = "self"

    def add(object_type, action_type, ts_str, target="", value=""):
        """
        Add a formatted event row.

        Args:
            object_type (str): Type of object.
            action_type (str): Action performed.
            ts_str (str): Timestamp string.
            target (str): Target content.
            value (str): Additional value.
        """
        if not ts_str:
            return
        try:
            ts = tiktok_utc_string_to_timestamp(ts_str, tz)
        except Exception:
            return

        rows.append({
            "platform": "tiktok",
            "object_type": object_type,
            "action_type": action_type,
            "username": username,
            "target": target or "",
            "value": value or "",
            "timestamp": ts,
        })

    watch = data.get("Your Activity", {}).get("Watch History", {}).get("VideoList", []) or []
    for it in watch:
        add("video", "watch", it.get("Date"))

    t = rows_to_table(rows)
    t = add_basic_time_columns(t)
    return filter_by_date_range(t, start_date, end_date)


# ============================================================
# Analysis helpers
# ============================================================

def events_by_hour(t: Table) -> Table:
    """
    Group events by hour.

    Args:
        t (Table): Input table.

    Returns:
        Table: Count of events by hour.
    """
    if "hour" not in t.labels:
        t = add_basic_time_columns(t)
    return t.group("hour").sort("count", descending=True)


def events_by_weekday(t: Table) -> Table:
    """
    Group events by weekday.

    Args:
        t (Table): Input table.

    Returns:
        Table: Count of events by weekday.
    """
    if "weekday" not in t.labels:
        t = add_basic_time_columns(t)
    return t.group("weekday").sort("count", descending=True)


def events_by_date(t: Table) -> Table:
    """
    Group events by date.

    Args:
        t (Table): Input table.

    Returns:
        Table: Count of events by date.
    """
    if "date" not in t.labels:
        t = add_basic_time_columns(t)
    return t.group("date").sort("date")


# ============================================================
# Combined
# ============================================================

def social_media_events(instagram_folder=None, tiktok_json=None,
                        tz="America/New_York", start_date=None, end_date=None) -> Table:
    """
    Build a combined social media events table.

    Args:
        instagram_folder (str | None): Instagram data path.
        tiktok_json (str | None): TikTok JSON path.
        tz (str): Target timezone.
        start_date (str | date, optional): Filter start date.
        end_date (str | date, optional): Filter end date.

    Returns:
        Table: Combined dataset.

    Raises:
        StudentInputError: If no data sources are found.
    """
    parts = []

    if instagram_folder and Path(instagram_folder).exists():
        parts.append(parse_metadata(instagram_folder, tz, start_date, end_date))

    if tiktok_json and Path(tiktok_json).exists():
        parts.append(tiktok_events(tiktok_json, tz, start_date, end_date))

    if not parts:
        _raise("No data found.")

    combined = parts[0]
    for p in parts[1:]:
        combined = combined.append(p)

    return combined