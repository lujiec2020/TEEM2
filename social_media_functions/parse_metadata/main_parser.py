import json
from pathlib import Path
from datetime import datetime, date, timedelta
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

def parse_user_date(s: str) -> date:
    """
    Accepts:
      - "12-16-2025" or "1-8-2026" (M-D-YYYY / MM-DD-YYYY)
      - "2025-12-16" (YYYY-MM-DD)
      - "12/16/2025" (MM/DD/YYYY)
    Returns: datetime.date
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
    _raise(
        "Invalid date format.\n"
        "Fix: use 'MM-DD-YYYY' (example: '12-16-2025') or 'YYYY-MM-DD' (example: '2025-12-16')."
    )


def filter_by_date_range(t: Table, start_date=None, end_date=None) -> Table:
    """
    Filters a table to [start_date, end_date] inclusive using timestamp_dt (if present)
    or timestamp (string) if needed.

    start_date/end_date can be:
      - None
      - strings like "12-16-2025" / "2025-12-16"
      - datetime.date objects
    """
    if start_date is None and end_date is None:
        return t

    start_d = parse_user_date(start_date) if not isinstance(start_date, date) else start_date
    end_d = parse_user_date(end_date) if not isinstance(end_date, date) else end_date

    if start_d and end_d and end_d < start_d:
        _raise(
            "end_date must be the same as or after start_date.\n"
            "Fix: check the year (example: Dec 2025 to Jan 2026 should end_date='1-8-2026')."
        )

    # Create/ensure a date column
    if "timestamp_dt" in t.labels:
        if "date" not in t.labels:
            t = t.with_column("date", t.apply(lambda d: d.date() if d else None, "timestamp_dt"))
    else:
        # last resort: try parsing timestamp string
        if "timestamp" not in t.labels:
            return t
        def _try_dt(ts):
            if ts is None:
                return None
            parts = str(ts).strip().split(" ")
            if len(parts) < 3:
                return None
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
    """Convert list[dict] -> datascience.Table with consistent columns."""
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
# Instagram helpers (unix -> local dt + format)
# ============================================================

def unix_to_local_dt(unix_ts: int, tz: str) -> datetime:
    return datetime.fromtimestamp(int(unix_ts), tz=ZoneInfo(tz))


def format_timestamp(dt_local: datetime) -> str:
    # "YYYY-MM-DD HH:MM:SS AM/PM EST/EDT"
    return dt_local.strftime("%Y-%m-%d %I:%M:%S %p %Z")


class EventTable:
    """Simple wrapper so older code can use .table."""
    def __init__(self, table: Table):
        self.table = table


# ============================================================
# Instagram parser (renamed: parse_metadata)
# ============================================================

def parse_metadata(path: str = "data/instagram_data", tz: str = "America/New_York",
                   start_date=None, end_date=None) -> Table:
    """
    Parse Instagram export data into a unified events Table.

    Scans the folder recursively for JSON files and extracts:
      - story likes
      - story poll responses
      - reel comments
      - post comments

    Returns a datascience.Table with:
      object_type, action_type, username, target, value,
      timestamp_dt, timestamp, timestamp_unix
    """
    folder = Path(path)

    if not folder.exists() or not folder.is_dir():
        _raise(
            f"Instagram folder not found: {folder}\n"
            "Fix: make sure your Instagram files are inside data/instagram_data/ "
            "or pass the correct folder path."
        )

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

        # STORY ACTIVITY
        if isinstance(data, dict):
            # story likes
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
                        except Exception:
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

            # story poll responses
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
                        except Exception:
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

        # REEL COMMENTS
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
                except Exception:
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

        # POST COMMENTS
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
                except Exception:
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

    base = rows_to_table(rows)
    base = filter_by_date_range(base, start_date=start_date, end_date=end_date)
    return base


# Back-compat alias for your classmates if needed:
instagram_events = lambda path="data/instagram_data", tz="America/New_York", start_date=None, end_date=None: EventTable(
    parse_metadata(path=path, tz=tz, start_date=start_date, end_date=end_date)
)


# ============================================================
# TikTok helpers
# ============================================================

def tiktok_utc_string_to_timestamp(ts_str: str, tz: str) -> str:
    """
    Input:  "YYYY-MM-DD HH:MM:SS" (TikTok UTC style)
    Output: "YYYY-MM-DD HH:MM:SS AM/PM EST/EDT"
    """
    dt_utc = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo("UTC"))
    dt_local = dt_utc.astimezone(ZoneInfo(tz))
    return dt_local.strftime("%Y-%m-%d %I:%M:%S %p %Z")


def add_basic_time_columns(t: Table) -> Table:
    """
    Adds: timestamp_dt, hour, weekday, date
    Works if timestamp ends with EST/EDT by ignoring final token.
    """
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
# TikTok main parser
# ============================================================

TIKTOK_COLUMNS = ["platform", "object_type", "action_type", "username", "target", "value", "timestamp"]

def tiktok_events(json_path: str = "data/tiktok_data/user_data_tiktok.json",
                 tz: str = "America/New_York",
                 start_date=None, end_date=None) -> Table:
    """
    Parse TikTok user_data_tiktok.json into a Table with columns:
      platform, object_type, action_type, username, target, value, timestamp
    Plus auto time columns: timestamp_dt, hour, weekday, date
    """
    path = Path(json_path)
    if not path.exists():
        _raise(
            f"TikTok file not found: {path}\n"
            "Fix: make sure your TikTok file is at data/tiktok_data/user_data_tiktok.json "
            "or pass the correct file path."
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
        add("video", "like", it.get("date") or it.get("Date"), target=(it.get("link") or it.get("Link") or it.get("url") or ""))

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

    rows.sort(key=lambda r: r["timestamp"])
    t = rows_to_table(rows, columns=TIKTOK_COLUMNS)
    t = add_basic_time_columns(t)
    t = filter_by_date_range(t, start_date=start_date, end_date=end_date)
    return t


# ============================================================
# TikTok analysis helpers
# ============================================================

def tiktok_watch_summary(t: Table):
    watch = t.where("action_type", "watch") if "action_type" in t.labels else t
    total = Table().with_columns("metric", ["total_watch_events"], "value", [watch.num_rows])
    by_hour = watch.group("hour").sort("count", descending=True) if "hour" in watch.labels else Table().with_columns("note", ["No 'hour' column."])
    by_weekday = watch.group("weekday").sort("count", descending=True) if "weekday" in watch.labels else Table().with_columns("note", ["No 'weekday' column."])
    by_date = watch.group("date").sort("date") if "date" in watch.labels else Table().with_columns("note", ["No 'date' column."])
    return {"total": total, "by_hour": by_hour, "by_weekday": by_weekday, "by_date": by_date}


def tiktok_late_night_binge(t: Table, start_hour: int = 23, end_hour: int = 4,
                           start_date=None, end_date=None):
    """
    Returns dict:
      - summary
      - late_by_date
    """
    t2 = filter_by_date_range(t, start_date=start_date, end_date=end_date)
    if "hour" not in t2.labels:
        t2 = add_basic_time_columns(t2)

    watch = t2.where("action_type", "watch") if "action_type" in t2.labels else t2
    if watch.num_rows == 0:
        return {"summary": Table().with_columns("note", ["No watch events found."])}

    late = watch.where("hour", lambda h: (h is not None) and (h >= start_hour or h <= end_hour))

    total_watch = watch.num_rows
    late_watch = late.num_rows
    late_share = (late_watch / total_watch) if total_watch else 0

    summary = Table().with_columns(
        "metric",
        ["date_range", "late_hours", "total_watch_events", "late_night_watch_events", "late_night_share"],
        "value",
        [
            f"{start_date} to {end_date}",
            f"{start_hour}:00–{end_hour}:59 (wrap)",
            total_watch,
            late_watch,
            f"{late_share:.2%}",
        ],
    )

    late_by_date = late.group("date").sort("date") if late.num_rows else Table().with_columns("note", ["No late-night watch events."])
    return {"summary": summary, "late_by_date": late_by_date}


def tiktok_doomscroll_indicator(t: Table, start_date=None, end_date=None,
                               late_start: int = 23, late_end: int = 4,
                               session_gap_minutes: int = 20, top_n_days: int = 10):
    """
    Returns dict:
      - summary
      - day_scores (top N)
    """
    t2 = filter_by_date_range(t, start_date=start_date, end_date=end_date)
    if "timestamp_dt" not in t2.labels or "hour" not in t2.labels or "date" not in t2.labels:
        t2 = add_basic_time_columns(t2)

    watch = t2.where("action_type", "watch") if "action_type" in t2.labels else t2
    if watch.num_rows == 0:
        return {"summary": Table().with_columns("note", ["No watch events found."])}

    by_day = watch.group("date").sort("count", descending=True)

    late = watch.where("hour", lambda h: (h is not None) and (h >= late_start or h <= late_end))
    late_by_day = late.group("date") if late.num_rows else Table().with_columns("date", [], "count", [])

    late_map = {}
    for d, c in zip(late_by_day.column("date"), late_by_day.column("count")):
        late_map[d] = c

    gap_seconds = session_gap_minutes * 60

    def session_count_for_date(day):
        day_tbl = watch.where("date", day).sort("timestamp_dt")
        dts = list(day_tbl.column("timestamp_dt"))
        if not dts:
            return 0
        sessions = 1
        for i in range(1, len(dts)):
            if (dts[i] - dts[i - 1]).total_seconds() > gap_seconds:
                sessions += 1
        return sessions

    rows = []
    for d, cnt in zip(by_day.column("date"), by_day.column("count")):
        late_cnt = late_map.get(d, 0)
        sessions = session_count_for_date(d)
        score = cnt + 2 * late_cnt + (10 if sessions >= 3 else 0)
        rows.append((d, cnt, late_cnt, sessions, score))

    day_scores = Table().with_columns(
        "date", [r[0] for r in rows],
        "watch_events", [r[1] for r in rows],
        "late_night_watch_events", [r[2] for r in rows],
        "sessions_est", [r[3] for r in rows],
        "doomscroll_score", [r[4] for r in rows],
    ).sort("doomscroll_score", descending=True)

    top_days = day_scores.take(range(min(top_n_days, day_scores.num_rows)))

    summary = Table().with_columns(
        "metric",
        ["date_range", "total_watch_events", "unique_watch_days", "session_gap_minutes", "late_hours"],
        "value",
        [
            f"{start_date} to {end_date}",
            watch.num_rows,
            len(set(watch.column("date"))),
            session_gap_minutes,
            f"{late_start}:00–{late_end}:59 (wrap)",
        ],
    )

    return {"summary": summary, "day_scores": top_days}


# ============================================================
# Combined (flexible: TikTok-only / Insta-only / both)
# ============================================================

FINAL_COLS = ["platform", "object_type", "action_type", "username", "target", "value", "timestamp"]

def _ensure_column(t: Table, col: str, default="") -> Table:
    if col not in t.labels:
        t = t.with_column(col, [default] * t.num_rows)
    return t


def _to_final_schema(t: Table, platform_name: str) -> Table:
    t = _ensure_column(t, "platform", platform_name)

    # support old TikTok "actor" name
    if "actor" in t.labels and "username" not in t.labels:
        t = t.relabel("actor", "username")

    t = _ensure_column(t, "username", "")
    for c in ["object_type", "action_type", "target", "value", "timestamp"]:
        t = _ensure_column(t, c, "")

    return t.select(*FINAL_COLS)


def social_media_events(
    instagram_folder: str | None = "data/instagram_data",
    tiktok_json: str | None = "data/tiktok_data/user_data_tiktok.json",
    tz: str = "America/New_York",
    start_date=None,
    end_date=None,
) -> Table:
    """
    Flexible combined table builder:
      - Instagram only if Instagram exists + TikTok missing/None
      - TikTok only if TikTok exists + Instagram missing/None
      - Both if both exist
    """
    parts = []

    if instagram_folder:
        folder = Path(instagram_folder)
        if folder.exists() and folder.is_dir():
            insta_tbl = parse_metadata(instagram_folder, tz=tz, start_date=start_date, end_date=end_date)
            parts.append(_to_final_schema(insta_tbl, "instagram"))

    if tiktok_json:
        fp = Path(tiktok_json)
        if fp.exists() and fp.is_file():
            tik_tbl = tiktok_events(tiktok_json, tz=tz, start_date=start_date, end_date=end_date)
            parts.append(_to_final_schema(tik_tbl, "tiktok"))

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

    try:
        combined = combined.sort("timestamp")
    except Exception:
        pass

    return combined


# ============================================================
# Generic breakdown helpers (work on combined or TikTok)
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