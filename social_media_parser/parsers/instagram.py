import json
from pathlib import Path
from datetime import datetime, date

from social_media_parser.utils import (
    rows_to_table,
    unix_to_local_dt,
    format_timestamp,
    index_by_active_day,  # 👈 NEW IMPORT
)
from social_media_parser.time_features import EventTable


# -------------------------
# Beginner-friendly errors
# -------------------------

class StudentInputError(Exception):
    """Friendly error for student mistakes (bad folder, bad dates, etc.)."""
    pass


def _raise(msg: str):
    raise StudentInputError("⚠️ " + msg)


# ---------------------------
# Date-range filter helper
# ---------------------------

def _parse_user_date(s: str) -> date:
    """
<<<<<<< HEAD
    Parse Instagram export data into a unified event table.

    This function scans a directory (and its subdirectories) for Instagram
    JSON export files and extracts structured activity such as story likes,
    poll responses, and comments on posts and reels.
    """
=======
    Accepts:
      - "12-16-2025" or "1-8-2026" (MM-DD-YYYY, M-D-YYYY)
      - "2025-12-16" (YYYY-MM-DD)
      - "12/16/2025" (MM/DD/YYYY)
    """
    s = str(s).strip()
    fmts = ["%m-%d-%Y", "%Y-%m-%d", "%m/%d/%Y"]
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
    Filter rows by date range using timestamp_dt.
    """
    if start_date is None and end_date is None:
        return table

    start_d = _parse_user_date(start_date) if start_date is not None else None
    end_d = _parse_user_date(end_date) if end_date is not None else None

    if start_d and end_d and end_d < start_d:
        _raise(
            "end_date must be the same as or after start_date.\n"
            "Fix: check the year (example: Dec 2025 to Jan 2026 should end_date='1-8-2026')."
        )

    if "timestamp_dt" not in table.labels:
        _raise(
            "Instagram table missing 'timestamp_dt'.\n"
            "Fix: make sure you are using parse_instagram/instagram_events from this project."
        )

    table = table.with_column("_date_only", table.apply(lambda dt: dt.date(), "timestamp_dt"))

    if start_d is not None:
        table = table.where("_date_only", lambda d: d >= start_d)
    if end_d is not None:
        table = table.where("_date_only", lambda d: d <= end_d)

    keep_cols = [c for c in table.labels if c != "_date_only"]
    return table.select(*keep_cols)


# ---------------------------
# Main Instagram parser
# ---------------------------

def parse_instagram(
    path: str = ".",
    tz: str = "America/New_York",
    start_date: str | None = None,
    end_date: str | None = None,
) -> EventTable:
>>>>>>> 63dd720 (new select function code and error handling)
    folder = Path(path)

    if not folder.exists() or not folder.is_dir():
        _raise(
            f"Folder not found: {folder}\n"
            "Fix: pass the folder that contains your Instagram JSON export files (example: 'data')."
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
        # STORY ACTIVITY
        # ---------------------------
        if isinstance(data, dict):

            if "story_activities_story_likes" in data:
                items = data.get("story_activities_story_likes", []) or []
                for item in items:
                    username = item.get("title", "") or ""
                    for entry in item.get("string_list_data", []) or []:
                        unix_ts = entry.get("timestamp")
                        if unix_ts is None:
                            continue
                        try:
                            unix_ts = int(unix_ts)
                        except (TypeError, ValueError):
                            continue
                        dt_local = unix_to_local_dt(unix_ts, tz)
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

            if "story_activities_polls" in data:
                items = data.get("story_activities_polls", []) or []
                for item in items:
                    username = item.get("title", "") or ""
                    for entry in item.get("string_list_data", []) or []:
                        unix_ts = entry.get("timestamp")
                        if unix_ts is None:
                            continue
                        try:
                            unix_ts = int(unix_ts)
                        except (TypeError, ValueError):
                            continue
                        value = entry.get("value", "") or ""
                        dt_local = unix_to_local_dt(unix_ts, tz)
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
        # REEL COMMENTS
        # ---------------------------
        if isinstance(data, dict) and "comments_reels_comments" in data:
            items = data.get("comments_reels_comments", []) or []
            for item in items:
                if not isinstance(item, dict):
                    continue
                string_map = item.get("string_map_data", {}) or {}
                comment_info = string_map.get("Comment", {}) or {}
                owner_info = string_map.get("Media Owner", {}) or {}
                time_info = string_map.get("Time", {}) or {}

                value = comment_info.get("value", "") or ""
                username = owner_info.get("value", "") or ""
                unix_ts = time_info.get("timestamp")
                if unix_ts is None:
                    continue
                try:
                    unix_ts = int(unix_ts)
                except (TypeError, ValueError):
                    continue
                dt_local = unix_to_local_dt(unix_ts, tz)
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
        # POST COMMENTS
        # ---------------------------
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue

                string_map = item.get("string_map_data", {}) or {}
                media_list = item.get("media_list_data", []) or []

                comment_info = string_map.get("Comment", {}) or {}
                owner_info = string_map.get("Media Owner", {}) or {}
                time_info = string_map.get("Time", {}) or {}

                value = comment_info.get("value", "") or ""
                username = owner_info.get("value", "") or ""
                unix_ts = time_info.get("timestamp")
                if unix_ts is None:
                    continue
                try:
                    unix_ts = int(unix_ts)
                except (TypeError, ValueError):
                    continue

                target = ""
                if media_list and isinstance(media_list[0], dict):
                    target = media_list[0].get("uri", "") or ""

                dt_local = unix_to_local_dt(unix_ts, tz)
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
    # Sort chronologically (oldest → newest)
    rows.sort(key=lambda r: r["timestamp_unix"])
    # Add relative day indexing
    rows = index_by_active_day(rows)

    base = rows_to_table(rows)
    base = filter_by_date_range(base, start_date=start_date, end_date=end_date)
    return EventTable(base)


instagram_events = parse_instagram