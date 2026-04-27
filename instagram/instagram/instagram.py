"""
Instagram parser for social media event analysis.

This module:
- Parses Instagram JSON export files (story likes, polls, reel comments, post comments).
- Converts timestamps to local timezone.
- Provides date filtering and reindexing utilities.
- Returns results as an EventTable for downstream analysis.

All functions are beginner-friendly and designed for use in data science courses.
"""

import json
from pathlib import Path
from datetime import datetime, date

from social_media_parser.utils import rows_to_table, unix_to_local_dt, format_timestamp
from social_media_parser.time_features import EventTable


# ============================================================
# Beginner-friendly errors
# ============================================================

class StudentInputError(Exception):
    """Friendly error for student mistakes (bad folder, bad dates, etc.)."""
    pass


def _raise(msg: str):
    """Raise a StudentInputError with a consistent prefix."""
    raise StudentInputError("Error: " + msg)


# ============================================================
# Date parsing + filtering
# ============================================================

def _parse_user_date(s: str) -> date:
    """
    Convert a user-provided date string into a `datetime.date`.

    Accepted formats
    ----------------
    - ``MM-DD-YYYY``  (e.g., ``12-16-2025``)
    - ``M-D-YYYY``    (e.g., ``1-8-2026``)
    - ``YYYY-MM-DD``  (e.g., ``2025-12-16``)
    - ``MM/DD/YYYY``  (e.g., ``12/16/2025``)

    Parameters
    ----------
    s : str
        A date string provided by the student.

    Returns
    -------
    datetime.date
        Parsed date object.

    Raises
    ------
    StudentInputError
        If the date format is invalid.
    """
    if s is None:
        return None

    s = str(s).strip()
    fmts = ["%m-%d-%Y", "%m-%d-%y", "%Y-%m-%d", "%m/%d/%Y"]

    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass

    _raise(
        "Invalid date format.\n"
        "Fix: use 'MM-DD-YYYY' (example: '12-16-2025') or 'YYYY-MM-DD' (example: '2025-12-16')."
    )


def filter_by_date_range(table, start_date=None, end_date=None):
    """
    Filter an Instagram events table by date range.

    Parameters
    ----------
    table : datascience.Table
        Table containing a ``timestamp_dt`` column.
    start_date : str or None
        Start of the date range.
    end_date : str or None
        End of the date range.

    Returns
    -------
    datascience.Table
        Filtered table containing only rows within the date range.

    Notes
    -----
    - If both dates are ``None``, the table is returned unchanged.
    - If ``timestamp_dt`` is missing, the table is returned unchanged.
    """
    if start_date is None and end_date is None:
        return table

    start_d = _parse_user_date(start_date) if start_date else None
    end_d = _parse_user_date(end_date) if end_date else None

    if start_d and end_d and end_d < start_d:
        _raise(
            "end_date must be the same as or after start_date.\n"
            "Fix: check the year (example: Dec 2025 to Jan 2026 should end_date='1-8-2026')."
        )

    if "timestamp_dt" not in table.labels:
        return table

    t = table.with_column("date", table.apply(lambda dt: dt.date() if dt else None, "timestamp_dt"))

    if start_d:
        t = t.where("date", lambda d: d is not None and d >= start_d)
    if end_d:
        t = t.where("date", lambda d: d is not None and d <= end_d)

    return t


# ============================================================
# Reindexing helper
# ============================================================

def reindex_instagram_by_date_range(t, start_str: str, end_str: str):
    """
    Reindex Instagram events within a date range using sequential integers.

    The first event in the range receives index 1, the next 2, and so on.

    Parameters
    ----------
    t : EventTable or datascience.Table
        Instagram event table or its underlying datascience.Table.
    start_str : str
        Start date (any accepted user format).
    end_str : str
        End date (any accepted user format).

    Returns
    -------
    datascience.Table
        Filtered table with a new column ``relative_range_index``.

    Raises
    ------
    StudentInputError
        If the date range is invalid.

    Examples
    --------
    >>> ig = parse_instagram("data")
    >>> subset = reindex_instagram_by_date_range(ig, "01-10-2024", "01-20-2024")
    >>> subset.labels
    ['object_type', 'action_type', ..., 'relative_range_index']
    """
    start_date = _parse_user_date(start_str)
    end_date = _parse_user_date(end_str)

    if end_date < start_date:
        _raise(
            "end_date must be the same as or after start_date.\n"
            "Fix: check the year (example: Dec 2025 to Jan 2026 should end_date='1-8-2026')."
        )

    base = t.table if hasattr(t, "table") else t

    if "timestamp_dt" not in base.labels:
        _raise("Instagram table is missing 'timestamp_dt'. This should never happen unless the parser failed.")

    base = base.with_column("date", base.apply(lambda dt: dt.date() if dt else None, "timestamp_dt"))

    filtered = base.where("date", lambda d: d is not None and start_date <= d <= end_date)

    if filtered.num_rows == 0:
        return filtered

    new_index = list(range(1, filtered.num_rows + 1))
    filtered = filtered.with_column("relative_range_index", new_index)

    return filtered


# ============================================================
# Main Instagram parser
# ============================================================

def parse_instagram(
    path: str = ".",
    tz: str = "America/New_York",
    start_date: str | None = None,
    end_date: str | None = None,
) -> EventTable:
    """
    Parse Instagram export data into a unified event table.

    Supported data types:
    - Story likes
    - Story poll responses
    - Reel comments
    - Post comments

    Parameters
    ----------
    path : str
        Folder containing Instagram JSON export files.
    tz : str
        Timezone for timestamp conversion.
    start_date : str or None
        Optional start date filter.
    end_date : str or None
        Optional end date filter.

    Returns
    -------
    EventTable
        Parsed Instagram events with standardized columns.

    Examples
    --------
    >>> ig = parse_instagram("data/instagram")
    >>> ig.table.num_rows
    482
    """
    if path is None or str(path).strip() == "":
        _raise("Instagram folder path is empty. Fix: pass a folder like 'data'.")

    folder = Path(path)

    if not folder.exists() or not folder.is_dir():
        _raise(
            f"Folder not found: {folder}\n"
            "Fix: pass the folder containing your downloaded Instagram JSON files."
        )

    rows = []
    json_files = sorted(folder.rglob("*.json"))

    if not json_files:
        return EventTable(rows_to_table([]))

    for fp in json_files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        # ----------------------------------------------------
        # STORY ACTIVITY (dict JSON)
        # ----------------------------------------------------
        if isinstance(data, dict):

            # Story likes
            if "story_activities_story_likes" in data:
                items = data.get("story_activities_story_likes", []) or []
                if not isinstance(items, list):
                    items = []

                for item in items:
                    if not isinstance(item, dict):
                        continue
                    username = item.get("title", "") or ""
                    string_list = item.get("string_list_data", []) or []
                    if not isinstance(string_list, list):
                        continue

                    for entry in string_list:
                        if not isinstance(entry, dict):
                            continue
                        unix_ts = entry.get("timestamp")
                        if unix_ts is None:
                            continue
                        try:
                            unix_ts = int(unix_ts)
                            dt_local = unix_to_local_dt(unix_ts, tz)
                        except Exception:
                            continue

                        rows.append({
                            "object_type": "story",
                            "action_type": "like",
                            "username": username,
                            "target": "",
                            "value": "",
                            "timestamp_dt": dt_local,
                            "timestamp": format_timestamp(dt_local),
                            "timestamp_unix": unix_ts,
                        })

            # Story poll responses
            if "story_activities_polls" in data:
                items = data.get("story_activities_polls", []) or []
                if not isinstance(items, list):
                    items = []

                for item in items:
                    if not isinstance(item, dict):
                        continue
                    username = item.get("title", "") or ""
                    string_list = item.get("string_list_data", []) or []
                    if not isinstance(string_list, list):
                        continue

                    for entry in string_list:
                        if not isinstance(entry, dict):
                            continue
                        unix_ts = entry.get("timestamp")
                        if unix_ts is None:
                            continue
                        try:
                            unix_ts = int(unix_ts)
                            dt_local = unix_to_local_dt(unix_ts, tz)
                        except Exception:
                            continue

                        value = entry.get("value", "") or ""

                        rows.append({
                            "object_type": "story",
                            "action_type": "poll_response",
                            "username": username,
                            "target": "",
                            "value": value,
                            "timestamp_dt": dt_local,
                            "timestamp": format_timestamp(dt_local),
                            "timestamp_unix": unix_ts,
                        })

        # ----------------------------------------------------
        # REEL COMMENTS (dict JSON)
        # ----------------------------------------------------
        if isinstance(data, dict) and "comments_reels_comments" in data:
            items = data.get("comments_reels_comments", []) or []
            if not isinstance(items, list):
                items = []

            for item in items:
                if not isinstance(item, dict):
                    continue

                string_map = item.get("string_map_data", {}) or {}
                if not isinstance(string_map, dict):
                    continue

                comment_info = string_map.get("Comment", {}) or {}
                owner_info = string_map.get("Media Owner", {}) or {}
                time_info = string_map.get("Time", {}) or {}

                if not all(isinstance(x, dict) for x in [comment_info, owner_info, time_info]):
                    continue

                value = comment_info.get("value", "") or ""
                username = owner_info.get("value", "") or ""
                unix_ts = time_info.get("timestamp")

                if unix_ts is None:
                    continue
                try:
                    unix_ts = int(unix_ts)
                    dt_local = unix_to_local_dt(unix_ts, tz)
                except Exception:
                    continue

                rows.append({
                    "object_type": "reel",
                    "action_type": "comment",
                    "username": username,
                    "target": "",
                    "value": value,
                    "timestamp_dt": dt_local,
                    "timestamp": format_timestamp(dt_local),
                    "timestamp_unix": unix_ts,
                })

        # ----------------------------------------------------
        # POST COMMENTS (list JSON)
        # ----------------------------------------------------
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue

                string_map = item.get("string_map_data", {}) or {}
                if not isinstance(string_map, dict):
                    continue

                media_list = item.get("media_list_data", []) or []
                if not isinstance(media_list, list):
                    media_list = []

                comment_info = string_map.get("Comment", {}) or {}
                owner_info = (
                    string_map.get("MediaOwner", {}) or
                    string_map.get("Media Owner", {}) or
                    {}
                )
                time_info = string_map.get("Time", {}) or {}

                if not all(isinstance(x, dict) for x in [comment_info, owner_info, time_info]):
                    continue

                value = comment_info.get("value", "") or ""
                username = owner_info.get("value", "") or ""
                unix_ts = time_info.get("timestamp")

                if unix_ts is None:
                    continue
                try:
                    unix_ts = int(unix_ts)
                    dt_local = unix_to_local_dt(unix_ts, tz)
                except Exception:
                    continue

                target = ""
                if media_list and isinstance(media_list[0], dict):
                    target = media_list[0].get("uri", "") or ""

                rows.append({
                    "object_type": "post",
                    "action_type": "comment",
                    "username": username,
                    "target": target,
                    "value": value,
                    "timestamp_dt": dt_local,
                    "timestamp": format_timestamp(dt_local),
                    "timestamp_unix": unix_ts,
                })

    base = rows_to_table(rows)
    base = filter_by_date_range(base, start_date=start_date, end_date=end_date)

    return EventTable(base)


# Backward compatibility
instagram_events = parse_instagram
