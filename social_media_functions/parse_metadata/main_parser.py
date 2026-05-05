"""
main_parser.py

Utilities for parsing and analyzing Instagram and TikTok data exports.

Expected data folder layout (default):
- data/
  - instagram_data/
      liked_posts.json
      post_comments_1.json
      reels_comments.json
      story_likes.json
  - tiktok_data/
      user_data_tiktok.json
"""

import json
from pathlib import Path
from datetime import datetime, date
from zoneinfo import ZoneInfo

from datascience import Table


# ============================================================
# Beginner-friendly errors
# ============================================================

class StudentInputError(Exception):
    """Friendly error for student mistakes (bad path, bad dates, etc.)."""
    pass


def _raise(msg: str):
    raise StudentInputError("⚠️ " + msg)


# ============================================================
# Date parsing + range filtering
# ============================================================

def parse_user_date(s) -> date | None:
    """Accepts: MM-DD-YYYY, YYYY-MM-DD, MM/DD/YYYY, or a datetime/date."""
    if s is None:
        return None
    if isinstance(s, date) and not isinstance(s, datetime):
        return s
    if isinstance(s, datetime):
        return s.date()

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


def filter_by_date_range(t: Table, start_date=None, end_date=None) -> Table:
    """Filters rows using the 'date' column if present, else creates it from timestamp_dt."""
    if start_date is None and end_date is None:
        return t

    start_d = parse_user_date(start_date)
    end_d = parse_user_date(end_date)

    if start_d and end_d and end_d < start_d:
        _raise(
            "end_date must be the same as or after start_date.\n"
            "Fix: check the year (example: Dec 2025 to Jan 2026 should end_date='1-8-2026')."
        )

    # Ensure timestamp_dt + date exist
    if "timestamp_dt" not in t.labels:
        if "timestamp" not in t.labels:
            return t

        def _try_dt(ts):
            if ts is None:
                return None
            parts = str(ts).split(" ")
            if len(parts) < 3:
                return None
            ts_no_tz = " ".join(parts[:-1])
            try:
                return datetime.strptime(ts_no_tz, "%Y-%m-%d %I:%M:%S %p")
            except Exception:
                return None

        t = t.with_column("timestamp_dt", t.apply(_try_dt, "timestamp"))

    if "date" not in t.labels:
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
    """Convert list[dict] -> datascience.Table with consistent columns."""
    if rows is None:
        rows = []

    if columns is None:
        cols = set()
        for r in rows:
            cols |= set(r.keys())
        columns = list(columns or sorted(cols))

    data = []
    for c in columns:
        data.append(c)
        data.append([r.get(c, "") for r in rows])

    return Table().with_columns(*data)


def ensure_column(t: Table, col: str, default="") -> Table:
    if col not in t.labels:
        t = t.with_column(col, [default] * t.num_rows)
    return t


def add_basic_time_columns(t: Table) -> Table:
    """
    Adds: timestamp_dt, hour, weekday, date
    Works when timestamp ends with EST/EDT by ignoring the last token.
    """
    def to_dt(ts):
        if ts is None:
            return None
        parts = str(ts).split(" ")
        if len(parts) < 3:
            return None
        ts_no_tz = " ".join(parts[:-1])  # drop EST/EDT
        try:
            return datetime.strptime(ts_no_tz, "%Y-%m-%d %I:%M:%S %p")
        except Exception:
            return None

    if "timestamp_dt" not in t.labels and "timestamp" in t.labels:
        t = t.with_column("timestamp_dt", t.apply(to_dt, "timestamp"))

    if "hour" not in t.labels and "timestamp_dt" in t.labels:
        t = t.with_column("hour", t.apply(lambda d: d.hour if d else None, "timestamp_dt"))

    if "weekday" not in t.labels and "timestamp_dt" in t.labels:
        t = t.with_column("weekday", t.apply(lambda d: d.strftime("%A") if d else None, "timestamp_dt"))

    if "date" not in t.labels and "timestamp_dt" in t.labels:
        t = t.with_column("date", t.apply(lambda d: d.date() if d else None, "timestamp_dt"))

    return t


# ============================================================
# Instagram helpers
# ============================================================

def unix_to_local_dt(unix_ts: int, tz: str) -> datetime:
    return datetime.fromtimestamp(int(unix_ts), tz=ZoneInfo(tz))


def format_timestamp(dt_local: datetime) -> str:
    return dt_local.strftime("%Y-%m-%d %I:%M:%S %p %Z")


# ============================================================
# Instagram parser
# ============================================================

def parse_metadata(
    path: str = "data/instagram_data",
    tz: str = "America/New_York",
    start_date=None,
    end_date=None,
) -> Table:
    """
    Parse Instagram export data into a unified events table.

    Supports files like:
      - liked_posts.json
      - post_comments_1.json
      - reels_comments.json
      - story_likes.json

    Output columns (base):
      platform, object_type, action_type, username, target, value, timestamp, timestamp_dt, hour, weekday, date
    """
    folder = Path(path)
    if not folder.exists() or not folder.is_dir():
        _raise(
            f"Instagram folder not found: {folder}\n"
            "Fix: make sure you have data/instagram_data/ (or pass the correct path)."
        )

    rows = []
    json_files = sorted(folder.rglob("*.json"))
    if not json_files:
        # Return an empty table with expected columns
        empty = Table().with_columns(
            "platform", [],
            "object_type", [],
            "action_type", [],
            "username", [],
            "target", [],
            "value", [],
            "timestamp", [],
        )
        empty = add_basic_time_columns(empty)
        return empty

    for fp in json_files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        if not isinstance(data, dict):
            continue

        # liked_posts.json (common IG export key)
        if "likes_media_likes" in data:
            items = data.get("likes_media_likes", []) or []
            for item in items:
                title = item.get("title", "") or ""
                for entry in item.get("string_list_data", []) or []:
                    unix_ts = entry.get("timestamp")
                    if unix_ts is None:
                        continue
                    try:
                        unix_ts = int(unix_ts)
                    except Exception:
                        continue
                    dt_local = unix_to_local_dt(unix_ts, tz)
                    rows.append({
                        "platform": "instagram",
                        "object_type": "post",
                        "action_type": "like",
                        "username": title,          # who you liked
                        "target": "",
                        "value": "",
                        "timestamp_dt": dt_local,
                        "timestamp": format_timestamp(dt_local),
                        "timestamp_unix": unix_ts,
                    })

        # post_comments_1.json (some exports use list OR dict; your dataset uses dict keys sometimes)
        if "comments_media_comments" in data:
            items = data.get("comments_media_comments", []) or []
            for item in items:
                title = item.get("title", "") or ""
                for entry in item.get("string_list_data", []) or []:
                    unix_ts = entry.get("timestamp")
                    val = entry.get("value", "") or ""
                    if unix_ts is None:
                        continue
                    try:
                        unix_ts = int(unix_ts)
                    except Exception:
                        continue
                    dt_local = unix_to_local_dt(unix_ts, tz)
                    rows.append({
                        "platform": "instagram",
                        "object_type": "post",
                        "action_type": "comment",
                        "username": title,
                        "target": "",
                        "value": val,
                        "timestamp_dt": dt_local,
                        "timestamp": format_timestamp(dt_local),
                        "timestamp_unix": unix_ts,
                    })

        # reels_comments.json
        if "comments_reels_comments" in data:
            items = data.get("comments_reels_comments", []) or []
            for item in items:
                title = item.get("title", "") or ""
                for entry in item.get("string_list_data", []) or []:
                    unix_ts = entry.get("timestamp")
                    val = entry.get("value", "") or ""
                    if unix_ts is None:
                        continue
                    try:
                        unix_ts = int(unix_ts)
                    except Exception:
                        continue
                    dt_local = unix_to_local_dt(unix_ts, tz)
                    rows.append({
                        "platform": "instagram",
                        "object_type": "reel",
                        "action_type": "comment",
                        "username": title,
                        "target": "",
                        "value": val,
                        "timestamp_dt": dt_local,
                        "timestamp": format_timestamp(dt_local),
                        "timestamp_unix": unix_ts,
                    })

        # story_likes.json
        if "story_activities_story_likes" in data:
            items = data.get("story_activities_story_likes", []) or []
            for item in items:
                title = item.get("title", "") or ""
                for entry in item.get("string_list_data", []) or []:
                    unix_ts = entry.get("timestamp")
                    if unix_ts is None:
                        continue
                    try:
                        unix_ts = int(unix_ts)
                    except Exception:
                        continue
                    dt_local = unix_to_local_dt(unix_ts, tz)
                    rows.append({
                        "platform": "instagram",
                        "object_type": "story",
                        "action_type": "like",
                        "username": title,
                        "target": "",
                        "value": "",
                        "timestamp_dt": dt_local,
                        "timestamp": format_timestamp(dt_local),
                        "timestamp_unix": unix_ts,
                    })

        # story poll responses (optional; if present in some exports)
        if "story_activities_polls" in data:
            items = data.get("story_activities_polls", []) or []
            for item in items:
                title = item.get("title", "") or ""
                for entry in item.get("string_list_data", []) or []:
                    unix_ts = entry.get("timestamp")
                    val = entry.get("value", "") or ""
                    if unix_ts is None:
                        continue
                    try:
                        unix_ts = int(unix_ts)
                    except Exception:
                        continue
                    dt_local = unix_to_local_dt(unix_ts, tz)
                    rows.append({
                        "platform": "instagram",
                        "object_type": "story",
                        "action_type": "poll_response",
                        "username": title,
                        "target": "",
                        "value": val,
                        "timestamp_dt": dt_local,
                        "timestamp": format_timestamp(dt_local),
                        "timestamp_unix": unix_ts,
                    })

    base = rows_to_table(rows)
    base = add_basic_time_columns(base)
    base = filter_by_date_range(base, start_date, end_date)

    # Keep beginner-friendly core columns first
    base = ensure_column(base, "platform", "instagram")
    base = ensure_column(base, "object_type", "")
    base = ensure_column(base, "action_type", "")
    base = ensure_column(base, "username", "")
    base = ensure_column(base, "target", "")
    base = ensure_column(base, "value", "")
    base = ensure_column(base, "timestamp", "")

    return base


# public alias for students (Instagram)
instagram_events = parse_metadata


# ============================================================
# TikTok helpers + parser
# ============================================================

def tiktok_utc_string_to_timestamp(ts_str: str, tz: str) -> str:
    dt_utc = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo("UTC"))
    dt_local = dt_utc.astimezone(ZoneInfo(tz))
    return dt_local.strftime("%Y-%m-%d %I:%M:%S %p %Z")


def tiktok_events(
    json_path: str = "data/tiktok_data/user_data_tiktok.json",
    tz: str = "America/New_York",
    start_date=None,
    end_date=None,
) -> Table:
    """
    Parse TikTok user_data_tiktok.json into an events table.

    Output columns:
      platform, object_type, action_type, username, target, value, timestamp, timestamp_dt, hour, weekday, date
    """
    path = Path(json_path)
    if not path.exists():
        _raise(
            f"TikTok file not found: {path}\n"
            "Fix: make sure you have data/tiktok_data/user_data_tiktok.json (or pass the correct path)."
        )

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

    # WATCH HISTORY
    watch = data.get("Your Activity", {}).get("Watch History", {}).get("VideoList", []) or []
    for it in watch:
        add("video", "watch", it.get("Date"), target=(it.get("Link") or it.get("link") or it.get("url") or ""))

    # LIKES
    likes = data.get("Likes and Favorites", {}).get("Like List", {}).get("ItemFavoriteList", []) or []
    for it in likes:
        add("video", "like", it.get("Date") or it.get("date"), target=(it.get("Link") or it.get("link") or it.get("url") or ""))

    # SEARCHES
    searches = data.get("Your Activity", {}).get("Searches", {}).get("SearchList", []) or []
    for it in searches:
        term = it.get("SearchTerm") or it.get("Search") or it.get("Term") or ""
        add("search", "search", it.get("Date") or it.get("date"), value=term)

    # COMMENTS
    comments = data.get("Comment", {}).get("Comments", {}).get("CommentsList", []) or []
    for it in comments:
        txt = it.get("comment") or it.get("Content") or it.get("content") or ""
        url = it.get("url") or it.get("Link") or it.get("link") or ""
        add("comment", "comment", it.get("date") or it.get("Date"), target=url, value=txt)

    # SHARES
    shares = data.get("Your Activity", {}).get("Share History", {}).get("ShareHistoryList", []) or []
    for it in shares:
        url = it.get("url") or it.get("Link") or it.get("SharedContent") or it.get("link") or ""
        method = it.get("Method") or ""
        add("share", "share", it.get("Date") or it.get("date"), target=url, value=method)

    # REPOSTS
    reposts = data.get("Your Activity", {}).get("Reposts", {}).get("RepostList", []) or []
    for it in reposts:
        url = it.get("url") or it.get("Link") or it.get("link") or ""
        add("video", "repost", it.get("Date") or it.get("date"), target=url)

    t = rows_to_table(rows)
    t = add_basic_time_columns(t)
    t = filter_by_date_range(t, start_date, end_date)

    return t


# ============================================================
# Combined (works if only one platform is available)
# ============================================================

FINAL_COLS = ["platform", "object_type", "action_type", "username", "target", "value", "timestamp"]


def _to_final_schema(t: Table, platform_name: str) -> Table:
    """
    Standardize any incoming table to:
      platform, object_type, action_type, username, target, value, timestamp
    and also keep time columns if present.
    """
    t = ensure_column(t, "platform", platform_name)
    t = ensure_column(t, "object_type", "")
    t = ensure_column(t, "action_type", "")
    t = ensure_column(t, "username", "")
    t = ensure_column(t, "target", "")
    t = ensure_column(t, "value", "")
    t = ensure_column(t, "timestamp", "")

    # keep core output columns first
    core = t.select(*FINAL_COLS)

    # if time columns exist, append them after (nice for student grouping)
    extra_cols = []
    for c in ["timestamp_dt", "hour", "weekday", "date"]:
        if c in t.labels:
            extra_cols.append(c)

    if extra_cols:
        # reattach extra cols from original t
        for c in extra_cols:
            core = core.with_column(c, t.column(c))

    return core


def social_media_events(
    instagram_folder: str | None = None,
    tiktok_json: str | None = None,
    tz: str = "America/New_York",
    start_date=None,
    end_date=None,
) -> Table:
    """
    Load Instagram and/or TikTok events and return ONE combined Table.

    If a student only has TikTok: pass only tiktok_json (or keep defaults).
    If a student only has Instagram: pass only instagram_folder (or keep defaults).
    """
    # defaults that match your new data folder structure
    if instagram_folder is None:
        instagram_folder = "data/instagram_data"
    if tiktok_json is None:
        tiktok_json = "data/tiktok_data/user_data_tiktok.json"

    parts = []

    # Instagram (only if folder exists)
    ig_path = Path(instagram_folder)
    if ig_path.exists() and ig_path.is_dir():
        ig_tbl = instagram_events(instagram_folder, tz=tz, start_date=start_date, end_date=end_date)
        if ig_tbl.num_rows > 0:
            parts.append(_to_final_schema(ig_tbl, "instagram"))

    # TikTok (only if file exists)
    tk_path = Path(tiktok_json)
    if tk_path.exists() and tk_path.is_file():
        tk_tbl = tiktok_events(tiktok_json, tz=tz, start_date=start_date, end_date=end_date)
        if tk_tbl.num_rows > 0:
            parts.append(_to_final_schema(tk_tbl, "tiktok"))

    if not parts:
        _raise(
            "No data found.\n"
            "Fix: make sure you have either:\n"
            "  - data/instagram_data/ with Instagram JSON files\n"
            "  - data/tiktok_data/user_data_tiktok.json\n"
            "Or pass correct paths into social_media_events(...)."
        )

    combined = parts[0]
    for p in parts[1:]:
        combined = combined.append(p)

    # sort if timestamp looks sortable
    if "timestamp" in combined.labels:
        try:
            combined = combined.sort("timestamp")
        except Exception:
            pass

    return combined


# ============================================================
# Simple “combined” analytics helpers
# ============================================================

def events_by_hour(t: Table) -> Table:
    if "hour" not in t.labels:
        t = add_basic_time_columns(t)
    return t.group("hour").sort("count", descending=True)


def events_by_weekday(t: Table) -> Table:
    if "weekday" not in t.labels:
        t = add_basic_time_columns(t)
    return t.group("weekday").sort("count", descending=True)


def events_by_date(t: Table) -> Table:
    if "date" not in t.labels:
        t = add_basic_time_columns(t)
    return t.group("date").sort("date")