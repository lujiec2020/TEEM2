import json
from pathlib import Path
from datetime import datetime, date

from datascience import Table
from src.Tools.utils import tiktok_utc_string_to_timestamp, rows_to_table

DEFAULT_TZ = "America/New_York"

COLUMNS = ["platform", "object_type", "action_type", "username", "target", "value", "timestamp"]


# ============================================================
# Beginner-friendly errors
# ============================================================

class StudentInputError(Exception):
    """Friendly error for student mistakes (bad path, bad dates, etc.)."""
    pass


def _raise(msg: str):
    """Raise a StudentInputError with a consistent prefix."""
    raise StudentInputError("⚠️ " + msg)


# ============================================================
# Date parsing + time column helpers
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


def add_basic_time_columns(t: Table) -> Table:
    """Adds: timestamp_dt, hour, weekday, date from timestamp string."""
    def to_dt(ts):
        parts = str(ts).split(" ")
        if len(parts) < 3:
            return None
        ts_no_tz = " ".join(parts[:-1])
        try:
            return datetime.strptime(ts_no_tz, "%Y-%m-%d %I:%M:%S %p")
        except Exception:
            return None

    t = t.with_column("timestamp_dt", t.apply(to_dt, "timestamp"))
    t = t.with_column("hour", t.apply(lambda d: d.hour if d else None, "timestamp_dt"))
    t = t.with_column("weekday", t.apply(lambda d: d.strftime("%A") if d else None, "timestamp_dt"))
    t = t.with_column("date", t.apply(lambda d: d.date() if d else None, "timestamp_dt"))
    return t


def filter_by_date_range(table: Table, start_date=None, end_date=None) -> Table:
    """Filter by start/end date using the 'date' column (created if missing)."""
    if start_date is None and end_date is None:
        return table

    start_d = _parse_user_date(start_date) if start_date is not None else None
    end_d = _parse_user_date(end_date) if end_date is not None else None

    if start_d and end_d and end_d < start_d:
        _raise(
            "end_date must be the same as or after start_date.\n"
            "Fix: check the year (example: Dec 2025 to Jan 2026 should end_date='1-8-2026')."
        )

    t = table
    if "date" not in t.labels:
        t = add_basic_time_columns(t)

    if start_d is not None:
        t = t.where("date", lambda d: d is not None and d >= start_d)
    if end_d is not None:
        t = t.where("date", lambda d: d is not None and d <= end_d)

    return t


# ============================================================
# Main TikTok parser
# ============================================================

def tiktok_events(
    json_path: str,
    tz: str = DEFAULT_TZ,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Table:
    """
    Parse TikTok user_data_tiktok.json into events table with columns:
      platform, object_type, action_type, username, target, value, timestamp
    """
    if json_path is None or str(json_path).strip() == "":
        _raise("TikTok JSON path is empty. Fix: pass something like 'data/user_data_tiktok.json'.")

    path = Path(json_path)
    if not path.exists():
        _raise(f"File not found: {path}\nFix: confirm the file path is correct.")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        _raise("Could not read TikTok JSON. Fix: make sure it's a valid .json export file.")

    rows = []
    username = "self"

    def add(platform, object_type, action_type, ts_str, target="", value=""):
        if not ts_str:
            return
        try:
            ts = tiktok_utc_string_to_timestamp(ts_str, tz)
        except Exception:
            return

        rows.append({
            "platform": platform,
            "object_type": object_type,
            "action_type": action_type,
            "username": username,
            "target": target or "",
            "value": value or "",
            "timestamp": ts,
        })

    # WATCH HISTORY
    watch = data.get("Your Activity", {}).get("Watch History", {}).get("VideoList", []) or []
    if not isinstance(watch, list):
        watch = []

    for it in watch:
        if not isinstance(it, dict):
            continue
        add(
            "tiktok",
            "video",
            "watch",
            it.get("Date"),
            target=(it.get("Link") or it.get("link") or it.get("url") or ""),
        )

    # LIKES
    likes = data.get("Likes and Favorites", {}).get("Like List", {}).get("ItemFavoriteList", []) or []
    if not isinstance(likes, list):
        likes = []

    for it in likes:
        if not isinstance(it, dict):
            continue
        add(
            "tiktok",
            "video",
            "like",
            it.get("date") or it.get("Date"),
            target=(it.get("link") or it.get("Link") or it.get("url") or ""),
        )

    # SEARCHES
    searches = data.get("Your Activity", {}).get("Searches", {}).get("SearchList", []) or []
    if not isinstance(searches, list):
        searches = []

    for it in searches:
        if not isinstance(it, dict):
            continue
        term = it.get("SearchTerm") or it.get("Search") or it.get("Term") or ""
        add("tiktok", "search", "search", it.get("Date") or it.get("date"), value=term)

    # COMMENTS
    comments = data.get("Comment", {}).get("Comments", {}).get("CommentsList", []) or []
    if not isinstance(comments, list):
        comments = []

    for it in comments:
        if not isinstance(it, dict):
            continue
        txt = it.get("comment") or it.get("Content") or it.get("content") or ""
        url = it.get("url") or it.get("Link") or it.get("link") or ""
        add("tiktok", "comment", "comment", it.get("date") or it.get("Date"), target=url, value=txt)

    # SHARES
    shares = data.get("Your Activity", {}).get("Share History", {}).get("ShareHistoryList", []) or []
    if not isinstance(shares, list):
        shares = []

    for it in shares:
        if not isinstance(it, dict):
            continue
        url = it.get("url") or it.get("Link") or it.get("SharedContent") or it.get("link") or ""
        method = it.get("Method") or ""
        add("tiktok", "share", "share", it.get("Date") or it.get("date"), target=url, value=method)

    # REPOSTS
    reposts = data.get("Your Activity", {}).get("Reposts", {}).get("RepostList", []) or []
    if not isinstance(reposts, list):
        reposts = []

    for it in reposts:
        if not isinstance(it, dict):
            continue
        url = it.get("url") or it.get("Link") or it.get("link") or ""
        add("tiktok", "video", "repost", it.get("Date") or it.get("date"), target=url)

    rows.sort(key=lambda r: r["timestamp"])

    t = rows_to_table(rows, columns=COLUMNS)
    t = add_basic_time_columns(t)
    t = filter_by_date_range(t, start_date=start_date, end_date=end_date)

    return t


# ============================================================
# Summaries + indicators
# ============================================================

def tiktok_watch_summary(t: Table):
    watch = t.where("action_type", "watch")

    total = Table().with_columns(
        "metric", ["total_watch_events"],
        "value", [watch.num_rows]
    )

    by_hour = watch.group("hour").sort("count", descending=True) if "hour" in watch.labels else \
        Table().with_columns("note", ["No 'hour' column found."])

    by_weekday = watch.group("weekday").sort("count", descending=True) if "weekday" in watch.labels else \
        Table().with_columns("note", ["No 'weekday' column found."])

    by_date = watch.group("date").sort("date") if "date" in watch.labels else \
        Table().with_columns("note", ["No 'date' column found."])

    return {"total": total, "by_hour": by_hour, "by_weekday": by_weekday, "by_date": by_date}


def tiktok_late_night_binge(
    t: Table,
    start_hour: int = 23,
    end_hour: int = 4,
    start_date: str | None = None,
    end_date: str | None = None,
):
    t2 = filter_by_date_range(t, start_date=start_date, end_date=end_date)
    watch = t2.where("action_type", "watch")

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
            f"{start_date} to {end_date}" if (start_date or end_date) else "all_time",
            f"{start_hour}:00–{end_hour}:59 (wrap)",
            total_watch,
            late_watch,
            f"{late_share:.2%}",
        ],
    )

    by_date = late.group("date").sort("date") if late.num_rows else Table().with_columns("note", ["No late-night watch events."])
    return {"summary": summary, "late_by_date": by_date}


def tiktok_doomscroll_indicator(
    t: Table,
    start_date: str | None = None,
    end_date: str | None = None,
    late_start: int = 23,
    late_end: int = 4,
    session_gap_minutes: int = 20,
    top_n_days: int = 10,
):
    t2 = filter_by_date_range(t, start_date=start_date, end_date=end_date)
    watch = t2.where("action_type", "watch")

    if watch.num_rows == 0:
        return {"summary": Table().with_columns("note", ["No watch events found."])}

    if "timestamp_dt" not in watch.labels:
        watch = add_basic_time_columns(watch)

    by_day = watch.group("date").sort("count", descending=True)

    late = watch.where("hour", lambda h: (h is not None) and (h >= late_start or h <= late_end))
    late_by_day = late.group("date") if late.num_rows else Table().with_columns("date", [], "count", [])

    late_map = {}
    if late_by_day.num_rows:
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
            if dts[i] and dts[i-1] and (dts[i] - dts[i-1]).total_seconds() > gap_seconds:
                sessions += 1
        return sessions

    dates = list(by_day.column("date"))
    counts = list(by_day.column("count"))

    rows = []
    for d, cnt in zip(dates, counts):
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

    top_days = (
        day_scores.take(range(min(top_n_days, day_scores.num_rows)))
        if day_scores.num_rows
        else day_scores
    )

    overall = Table().with_columns(
        "metric",
        [
            "date_range",
            "total_watch_events",
            "unique_watch_days",
            "session_gap_minutes",
            "late_hours",
        ],
        "value",
        [
            f"{start_date} to {end_date}" if (start_date or end_date) else "all_time",
            watch.num_rows,
            len(set(watch.column("date"))),
            session_gap_minutes,
            f"{late_start}:00–{late_end}:59 (wrap)",
        ],
    )

    return {"summary": overall, "day_scores": top_days}
