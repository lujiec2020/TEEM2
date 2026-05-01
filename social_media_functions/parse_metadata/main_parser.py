"""
social_media_parser.py

Utilities for parsing and analyzing Instagram and TikTok data exports.
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
    pass


def _raise(msg: str):
    raise StudentInputError("⚠️ " + msg)


# ============================================================
# Date parsing + range filtering
# ============================================================

def parse_user_date(s: str) -> date:
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
    return datetime.fromtimestamp(int(unix_ts), tz=ZoneInfo(tz))


def format_timestamp(dt_local: datetime) -> str:
    return dt_local.strftime("%Y-%m-%d %I:%M:%S %p %Z")


# ============================================================
# FIXED INSTAGRAM PARSER
# ============================================================

def parse_metadata(path: str = "data/instagram_data", tz: str = "America/New_York",
                   start_date=None, end_date=None) -> Table:
    """
    Parse Instagram export data into a unified events table.

    Supports:
        - liked_posts.json
        - post_comments_1.json
        - reels_comments.json
        - story_likes.json
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

        # ----------------------------------------------------
        # 1. liked_posts.json
        # ----------------------------------------------------
        if "likes_media_likes" in data:
            for item in data["likes_media_likes"]:
                for entry in item.get("string_list_data", []):
                    unix_ts = entry.get("timestamp")
                    if unix_ts:
                        dt_local = unix_to_local_dt(unix_ts, tz)
                        rows.append({
                            "platform": "instagram",
                            "object_type": "post",
                            "action_type": "like",
                            "username": entry.get("value", ""),
                            "target": item.get("title", ""),
                            "value": "",
                            "timestamp_dt": dt_local,
                            "timestamp": format_timestamp(dt_local),
                            "timestamp_unix": unix_ts,
                        })

        # ----------------------------------------------------
        # 2. post_comments_1.json
        # ----------------------------------------------------
        if "comments_media_comments" in data:
            for item in data["comments_media_comments"]:
                for entry in item.get("string_list_data", []):
                    unix_ts = entry.get("timestamp")
                    if unix_ts:
                        dt_local = unix_to_local_dt(unix_ts, tz)
                        rows.append({
                            "platform": "instagram",
                            "object_type": "post",
                            "action_type": "comment",
                            "username": entry.get("value", ""),
                            "target": item.get("title", ""),
                            "value": entry.get("value", ""),
                            "timestamp_dt": dt_local,
                            "timestamp": format_timestamp(dt_local),
                            "timestamp_unix": unix_ts,
                        })

        # ----------------------------------------------------
        # 3. reels_comments.json
        # ----------------------------------------------------
        if "comments_reels_comments" in data:
            for item in data["comments_reels_comments"]:
                for entry in item.get("string_list_data", []):
                    unix_ts = entry.get("timestamp")
                    if unix_ts:
                        dt_local = unix_to_local_dt(unix_ts, tz)
                        rows.append({
                            "platform": "instagram",
                            "object_type": "reel",
                            "action_type": "comment",
                            "username": entry.get("value", ""),
                            "target": item.get("title", ""),
                            "value": entry.get("value", ""),
                            "timestamp_dt": dt_local,
                            "timestamp": format_timestamp(dt_local),
                            "timestamp_unix": unix_ts,
                        })

        # ----------------------------------------------------
        # 4. story_likes.json
        # ----------------------------------------------------
        if "story_activities_story_likes" in data:
            for item in data["story_activities_story_likes"]:
                for entry in item.get("string_list_data", []):
                    unix_ts = entry.get("timestamp")
                    if unix_ts:
                        dt_local = unix_to_local_dt(unix_ts, tz)
                        rows.append({
                            "platform": "instagram",
                            "object_type": "story",
                            "action_type": "like",
                            "username": entry.get("value", ""),
                            "target": item.get("title", ""),
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
    dt_utc = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo("UTC"))
    dt_local = dt_utc.astimezone(ZoneInfo(tz))
    return dt_local.strftime("%Y-%m-%d %I:%M:%S %p %Z")


def add_basic_time_columns(t: Table) -> Table:
    def to_dt(ts):
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

    path = Path(json_path)
    if not path.exists():
        _raise(f"TikTok file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []
    username = "self"

    def add(object_type, action_type, ts_str, target="", value=""):
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
# Combined
# ============================================================

def social_media_events(instagram_folder=None, tiktok_json=None,
                        tz="America/New_York", start_date=None, end_date=None):
    """
    Load Instagram and/or TikTok events and return a combined table.

    Args:
        instagram_folder (str | None): Path to Instagram data folder.
        tiktok_json (str | None): Path to TikTok JSON file.
        tz (str): Timezone for timestamp conversion.
        start_date (str | date | None): Optional filter start date.
        end_date (str | date | None): Optional filter end date.

    Returns:
        Table: Combined datascience Table of events.
    """

    parts = []

    # Instagram
    if instagram_folder and Path(instagram_folder).exists():
        try:
            ig = parse_metadata(instagram_folder, tz, start_date, end_date)
            parts.append(ig)
        except Exception as e:
            raise StudentInputError(f"Error loading Instagram data: {e}")

    # TikTok
    if tiktok_json and Path(tiktok_json).exists():
        try:
            tt = tiktok_events(tiktok_json, tz, start_date, end_date)
            parts.append(tt)
        except Exception as e:
            raise StudentInputError(f"Error loading TikTok data: {e}")

    if not parts:
        raise StudentInputError("No valid Instagram or TikTok data found.")

    # Start with the first table
    combined = parts[0]

    # Append the rest, aligning columns each time
    for p in parts[1:]:

        # Add missing columns to p
        for col in combined.labels:
            if col not in p.labels:
                p = p.with_column(col, [""] * p.num_rows)

        # Add missing columns to combined
        for col in p.labels:
            if col not in combined.labels:
                combined = combined.with_column(col, [""] * combined.num_rows)

        # Now safe to append
        combined = combined.append(p)

    return combined
