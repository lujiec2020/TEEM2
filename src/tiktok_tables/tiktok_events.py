import json
from pathlib import Path
from datetime import datetime, timedelta, date

from datascience import Table

from src.Tools.utils import tiktok_utc_string_to_timestamp, rows_to_table

DEFAULT_TZ = "America/New_York"
COLUMNS = ["platform", "object_type", "action_type", "username", "target", "value", "timestamp"]


# -------------------------
# Beginner-friendly errors
# -------------------------

class StudentInputError(Exception):
    """Friendly error for student mistakes (bad path, bad dates, etc.)."""
    pass


def _raise(msg: str):
    raise StudentInputError("⚠️ " + msg)


# -------------------------
# Date parsing + range filter
# -------------------------

def _parse_user_date(s: str) -> date:
    """
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


def filter_by_date_range(t: Table, start_date=None, end_date=None) -> Table:
    """Filter rows by date range using the existing 'date' column."""
    if start_date is None and end_date is None:
        return t

    if "date" not in t.labels:
        _raise(
            "This table has no 'date' column.\n"
            "Fix: make sure you built the table using tiktok_events(...) (it adds date/hour automatically)."
        )

    start_d = _parse_user_date(start_date) if start_date is not None else None
    end_d = _parse_user_date(end_date) if end_date is not None else None

    if start_d and end_d and end_d < start_d:
        _raise(
            "end_date must be the same as or after start_date.\n"
            "Fix: check the year (example: Dec 2025 to Jan 2026 should end_date='1-8-2026')."
        )

    if start_d is not None:
        t = t.where("date", lambda d: d is not None and d >= start_d)
    if end_d is not None:
        t = t.where("date", lambda d: d is not None and d <= end_d)

    return t


# -------------------------
# Time features
# -------------------------

def add_basic_time_columns(t: Table) -> Table:
    """
    Adds: timestamp_dt, hour, weekday, date

    Expects timestamp like:
      'YYYY-MM-DD HH:MM:SS AM/PM EDT'
    """
    def to_dt(ts):
        try:
            ts_no_tz = " ".join(str(ts).split(" ")[:-1])  # drop EST/EDT token
            return datetime.strptime(ts_no_tz, "%Y-%m-%d %I:%M:%S %p")
        except Exception:
            _raise(
                "Could not parse a timestamp into a datetime.\n"
                "Fix: make sure your 'timestamp' column looks like '2019-07-15 10:23:42 PM EDT'.\n"
                "Tip: Restart Kernel after editing .py files."
            )

    t = t.with_column("timestamp_dt", t.apply(to_dt, "timestamp"))
    t = t.with_column("hour", t.apply(lambda d: d.hour if d else None, "timestamp_dt"))
    t = t.with_column("weekday", t.apply(lambda d: d.strftime("%A") if d else None, "timestamp_dt"))
    t = t.with_column("date", t.apply(lambda d: d.date() if d else None, "timestamp_dt"))
    return t


# -------------------------
# Main TikTok parser
# -------------------------

def tiktok_events(
    json_path: str,
    tz: str = DEFAULT_TZ,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Table:
    """
    Parse TikTok user_data_tiktok.json into a beginner-friendly events Table.

    Optional date filtering:
      start_date="12-16-2025", end_date="1-8-2026"
    """
    path = Path(json_path)
    if not path.exists():
        _raise(
            f"File not found: {path}\n"
            "Fix: put your TikTok file in the data/ folder and call:\n"
            "  tiktok_events('data/user_data_tiktok.json')"
        )

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        _raise(
            "Could not read your TikTok JSON file.\n"
            "Fix: make sure it is a valid JSON export (not HTML) and it is not corrupted."
        )

    rows = []
    username = "self"

    def add(platform, object_type, action_type, ts_str, target="", value=""):
        if not ts_str:
            return
        try:
            ts = tiktok_utc_string_to_timestamp(ts_str, tz)
        except Exception:
            # If timezone string is wrong, students should see a helpful message
            _raise(
                f"Could not convert timestamp using timezone '{tz}'.\n"
                "Fix: try tz='America/New_York' (EST) or tz='America/Los_Angeles' (PST)."
            )

        rows.append(
            {
                "platform": platform,
                "object_type": object_type,
                "action_type": action_type,
                "username": username,
                "target": target or "",
                "value": value or "",
                "timestamp": ts,
            }
        )

    # WATCH HISTORY
    watch = data.get("Your Activity", {}).get("Watch History", {}).get("VideoList", []) or []
    for it in watch:
        add("tiktok", "video", "watch", it.get("Date"),
            target=(it.get("Link") or it.get("link") or it.get("url") or ""))

    # LIKES
    likes = data.get("Likes and Favorites", {}).get("Like List", {}).get("ItemFavoriteList", []) or []
    for it in likes:
        add("tiktok", "video", "like", it.get("date") or it.get("Date"),
            target=(it.get("link") or it.get("Link") or it.get("url") or ""))

    # SEARCHES
    searches = data.get("Your Activity", {}).get("Searches", {}).get("SearchList", []) or []
    for it in searches:
        term = it.get("SearchTerm") or it.get("Search") or it.get("Term") or ""
        add("tiktok", "search", "search", it.get("Date") or it.get("date"), value=term)

    # COMMENTS
    comments = data.get("Comment", {}).get("Comments", {}).get("CommentsList", []) or []
    for it in comments:
        txt = it.get("comment") or it.get("Content") or it.get("content") or ""
        url = it.get("url") or it.get("Link") or it.get("link") or ""
        add("tiktok", "comment", "comment", it.get("date") or it.get("Date"), target=url, value=txt)

    # SHARES
    shares = data.get("Your Activity", {}).get("Share History", {}).get("ShareHistoryList", []) or []
    for it in shares:
        url = it.get("url") or it.get("Link") or it.get("SharedContent") or it.get("link") or ""
        method = it.get("Method") or ""
        add("tiktok", "share", "share", it.get("Date") or it.get("date"), target=url, value=method)

    # REPOSTS
    reposts = data.get("Your Activity", {}).get("Reposts", {}).get("RepostList", []) or []
    for it in reposts:
        url = it.get("url") or it.get("Link") or it.get("link") or ""
        add("tiktok", "video", "repost", it.get("Date") or it.get("date"), target=url)

    rows.sort(key=lambda r: r["timestamp"])

    t = rows_to_table(rows, columns=COLUMNS)
    t = add_basic_time_columns(t)
    t = filter_by_date_range(t, start_date=start_date, end_date=end_date)
    return t


# -------------------------
# Summaries / indicators
# -------------------------

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
            f"{start_date or 'ALL'} to {end_date or 'ALL'}",
            f"{start_hour}:00–{end_hour}:59 (wrap)",
            total_watch,
            late_watch,
            f"{late_share:.2%}",
        ],
    )

    late_by_date = late.group("date").sort("date") if late.num_rows else \
        Table().with_columns("note", ["No late-night watch events."])

    return {"summary": summary, "late_by_date": late_by_date}


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
            if (dts[i] - dts[i - 1]).total_seconds() > gap_seconds:
                sessions += 1
        return sessions

    dates = list(by_day.column("date"))
    counts = list(by_day.column("count"))

    rows = []
    for d, cnt in zip(dates, counts):
        late_cnt = late_map.get(d, 0)
        sessions = session_count_for_date(d)
        score = cnt + 2 * late_cnt + (10 if sessions >= 3 else 0)

        rows.append({
            "date": d,
            "watch_events": cnt,
            "late_night_watch_events": late_cnt,
            "sessions_est": sessions,
            "doomscroll_score": score,
        })

    day_scores = Table().with_columns(
        "date", [r["date"] for r in rows],
        "watch_events", [r["watch_events"] for r in rows],
        "late_night_watch_events", [r["late_night_watch_events"] for r in rows],
        "sessions_est", [r["sessions_est"] for r in rows],
        "doomscroll_score", [r["doomscroll_score"] for r in rows],
    ).sort("doomscroll_score", descending=True)

    top_days = day_scores.take(range(min(top_n_days, day_scores.num_rows))) if day_scores.num_rows else day_scores

    summary = Table().with_columns(
        "metric",
        ["date_range", "total_watch_events", "unique_watch_days", "session_gap_minutes", "late_hours"],
        "value",
        [
            f"{start_date or 'ALL'} to {end_date or 'ALL'}",
            watch.num_rows,
            len(set(watch.column("date"))),
            session_gap_minutes,
            f"{late_start}:00–{late_end}:59 (wrap)",
        ],
    )

    return {"summary": summary, "day_scores": top_days}