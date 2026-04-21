import json
from pathlib import Path
from datetime import datetime, date

from social_media_parser.utils import rows_to_table, unix_to_local_dt, format_timestamp
from social_media_parser.time_features import EventTable


# -------------------------
# Beginner-friendly errors
# -------------------------

class StudentInputError(Exception):
    """Friendly error for student mistakes (bad folder, bad dates, etc.)."""
    pass


def _raise(msg: str):
    raise StudentInputError("Error: " + msg)


# -------------------------
# Date parsing + filtering
# -------------------------

def _parse_user_date(s: str) -> date:
    """
    Accepts:
      - "12-16-2025" or "1-8-2026" (MM-DD-YYYY / M-D-YYYY)
      - "2025-12-16" (YYYY-MM-DD)
      - "12/16/2025" (MM/DD/YYYY)
    Returns a datetime.date.
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
    Filters a datascience.Table by date range using timestamp_dt.
    start_date/end_date can be None.
    """
    if start_date is None and end_date is None:
        return table

    start_d = _parse_user_date(start_date) if start_date is not None else None
    end_d = _parse_user_date(end_date) if end_date is not None else None

    if start_d is not None and end_d is not None and end_d < start_d:
        _raise(
            "end_date must be the same as or after start_date.\n"
            "Fix: check the year (example: Dec 2025 to Jan 2026 should end_date='1-8-2026')."
        )

    if "timestamp_dt" not in table.labels:
        return table

    # create date column for filtering
    t = table.with_column("date", table.apply(lambda dt: dt.date() if dt else None, "timestamp_dt"))

    if start_d is not None:
        t = t.where("date", lambda d: d is not None and d >= start_d)
    if end_d is not None:
        t = t.where("date", lambda d: d is not None and d <= end_d)

    return t


# -------------------------
# NEW: Reindex Instagram by date range
# -------------------------

def reindex_instagram_by_date_range(t, start_str: str, end_str: str):
    """
    Reindex Instagram events within a date range using 1, 2, 3, ...
    Date format: 'MM-DD-YYYY' (also accepts YYYY-MM-DD and MM/DD/YYYY).
    Works on EventTable or raw datascience.Table.
    """

    # Convert user input to date objects
    start_date = _parse_user_date(start_str)
    end_date = _parse_user_date(end_str)

    if end_date < start_date:
        _raise(
            "end_date must be the same as or after start_date.\n"
            "Fix: check the year (example: Dec 2025 to Jan 2026 should end_date='1-8-2026')."
        )

    # If user passed an EventTable, extract the underlying table
    if hasattr(t, "table"):
        base = t.table
    else:
        base = t

    # Ensure timestamp_dt exists
    if "timestamp_dt" not in base.labels:
        _raise("Instagram table is missing 'timestamp_dt'. This should never happen unless the parser failed.")

    # Add a date column for filtering
    base = base.with_column(
        "date",
        base.apply(lambda dt: dt.date() if dt else None, "timestamp_dt")
    )

    # Filter rows inside the date range
    filtered = base.where(
        "date",
        lambda d: d is not None and start_date <= d <= end_date
    )

    # If no rows, return empty table
    if filtered.num_rows == 0:
        return filtered

    # Add sequential index column
    new_index = list(range(1, filtered.num_rows + 1))
    filtered = filtered.with_column("relative_range_index", new_index)

    return filtered


# -------------------------
# Main parser
# -------------------------

def parse_instagram(
    path: str = ".",
    tz: str = "America/New_York",
    start_date: str | None = None,
    end_date: str | None = None,
) -> EventTable:
    """
    Parse Instagram export data into a unified event table.

    Parameters
    ----------
    path : str
        Folder containing Instagram JSON export files.
    tz : str
        Timezone for timestamp conversion.
    start_date / end_date : str | None
        Optional date range filter.
    """
    if path is None or str(path).strip() == "":
        _raise("Instagram folder path is empty. Fix: pass a folder like 'data' (or '.' for current folder).")

    folder = Path(path)

    if not folder.exists() or not folder.is_dir():
        _raise(
            f"Folder not found: {folder}\n"
            "Fix: pass the folder containing your downloaded Instagram JSON files (example: 'data')."
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

        # ---------------------------
        # STORY ACTIVITY (dict JSON)
        # ---------------------------
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
                        except (TypeError, ValueError):
                            continue

                        try:
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
                        except (TypeError, ValueError):
                            continue

                        value = entry.get("value", "") or ""
                        try:
                            dt_local = unix_to_local_dt(unix_ts, tz)
                        except Exception:
                            continue

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

        # ---------------------------
        # REEL COMMENTS (dict JSON)
        # ---------------------------
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

                if not isinstance(comment_info, dict) or not isinstance(owner_info, dict) or not isinstance(time_info, dict):
                    continue

                value = comment_info.get("value", "") or ""
                username = owner_info.get("value", "") or ""
                unix_ts = time_info.get("timestamp")

                if unix_ts is None:
                    continue
                try:
                    unix_ts = int(unix_ts)
                except Exception:
                    continue

                try:
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

        # ---------------------------
        # POST COMMENTS (list JSON)
        # ---------------------------
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
                owner_info = string_map.get("MediaOwner", {}) or string_map.get("Media Owner", {}) or {}
                time_info = string_map.get("Time", {}) or {}

                if not isinstance(comment_info, dict) or not isinstance(owner_info, dict) or not isinstance(time_info, dict):
                    continue

                value = comment_info.get("value", "") or ""
                username = owner_info.get("value", "") or ""
                unix_ts = time_info.get("timestamp")

                if unix_ts is None:
                    continue
                try:
                    unix_ts = int(unix_ts)
                except Exception:
                    continue

                target = ""
                if media_list and isinstance(media_list[0], dict):
                    target = media_list[0].get("uri", "") or ""

                try:
                    dt_local = unix_to_local_dt(unix_ts, tz)
                except Exception:
                    continue

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


# Compatibility for older code versions
instagram_events = parse_instagram
