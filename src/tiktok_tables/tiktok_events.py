import json
from pathlib import Path
from datetime import datetime, timedelta

from datascience import Table

from src.Tools.utils import tiktok_utc_string_to_timestamp, rows_to_table

DEFAULT_TZ = "America/New_York"

# Use username to stay consistent with your merged/instagram schema
COLUMNS = ["platform", "object_type", "action_type", "username", "target", "value", "timestamp"]


# -------------------------
# Time feature helpers
# -------------------------

def add_basic_time_columns(t: Table) -> Table:
    """
    Adds: timestamp_dt, hour, weekday, date

    Works even if timestamp ends with EST/EDT by ignoring the last token.
    Example: '2019-07-15 10:23:42 PM EDT'
    """
    def to_dt(ts):
        # drop timezone token (EST/EDT/etc.)
        ts_no_tz = " ".join(str(ts).split(" ")[:-1])
        return datetime.strptime(ts_no_tz, "%Y-%m-%d %I:%M:%S %p")

    t = t.with_column("timestamp_dt", t.apply(to_dt, "timestamp"))
    t = t.with_column("hour", t.apply(lambda d: d.hour if d else None, "timestamp_dt"))
    t = t.with_column("weekday", t.apply(lambda d: d.strftime("%A") if d else None, "timestamp_dt"))
    t = t.with_column("date", t.apply(lambda d: d.date() if d else None, "timestamp_dt"))
    return t


def _filter_window_by_latest_date(t: Table, window: str | None) -> Table:
    """
    Filter by a time window relative to the latest date in the dataset.
    window options: None or "all", "1_week", "1_month", "3_month", "6_month", "1_year"
    """
    if window is None or str(window).lower() in ("all", ""):
        return t

    days_map = {
        "1_week": 7,
        "1_month": 30,
        "3_month": 90,
        "6_month": 180,
        "1_year": 365,
    }
    window = str(window).lower().strip()
    if window not in days_map:
        raise ValueError(f"Invalid window '{window}'. Use one of: {list(days_map.keys())} or 'all'.")

    if "date" not in t.labels:
        t = add_basic_time_columns(t)

    dates = [d for d in t.column("date") if d is not None]
    if not dates:
        return t

    latest = max(dates)
    cutoff = latest - timedelta(days=days_map[window])
    return t.where("date", lambda d: d is not None and d >= cutoff)


# -------------------------
# Main TikTok parser
# -------------------------

def tiktok_events(json_path: str, tz: str = DEFAULT_TZ) -> Table:
    """
    Parse TikTok user_data_tiktok.json into a beginner-friendly events Table with columns:
      platform, object_type, action_type, username, target, value, timestamp

    Also auto-adds:
      timestamp_dt, hour, weekday, date
    """
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []
    username = "self"

    def add(platform, object_type, action_type, ts_str, target="", value=""):
        if not ts_str:
            return
        try:
            ts = tiktok_utc_string_to_timestamp(ts_str, tz)
        except Exception:
            return

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
        add(
            "tiktok",
            "video",
            "watch",
            it.get("Date"),
            target=(it.get("Link") or it.get("link") or it.get("url") or ""),
        )

    # LIKES
    likes = data.get("Likes and Favorites", {}).get("Like List", {}).get("ItemFavoriteList", []) or []
    for it in likes:
        add(
            "tiktok",
            "video",
            "like",
            it.get("date") or it.get("Date"),
            target=(it.get("link") or it.get("Link") or it.get("url") or ""),
        )

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

    # Sort by timestamp string (safe because it starts with YYYY-MM-DD)
    rows.sort(key=lambda r: r["timestamp"])

    # Build base events table
    t = rows_to_table(rows, columns=COLUMNS)

    # Add hour/weekday/date automatically
    t = add_basic_time_columns(t)

    return t


# -------------------------
# Existing summary function
# -------------------------

def tiktok_watch_summary(t: Table):
    """
    Beginner-friendly TikTok-only watch summary.
    Returns dict of small Tables students can .show()
    """
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


# -------------------------
# NEW: Late-night binge scrolling
# -------------------------

def tiktok_late_night_binge(
    t: Table,
    start_hour: int = 23,
    end_hour: int = 4,
    window: str | None = "all",
):
    """
    Late-night binge scrolling indicator (TikTok-only).
    Counts watch events occurring late night.

    Default window: all data (same as import)
    Default late-night window: 11PM–4AM
      - hours >= 23 OR hours <= 4

    Returns:
      dict with summary table + by_date table
    """
    t2 = _filter_window_by_latest_date(t, window)
    watch = t2.where("action_type", "watch")

    if watch.num_rows == 0:
        return {"summary": Table().with_columns("note", ["No watch events found."])}

    # Late-night mask (wrap around midnight)
    late = watch.where("hour", lambda h: (h is not None) and (h >= start_hour or h <= end_hour))

    total_watch = watch.num_rows
    late_watch = late.num_rows
    late_share = (late_watch / total_watch) if total_watch else 0

    summary = Table().with_columns(
        "metric",
        ["window", "late_hours", "total_watch_events", "late_night_watch_events", "late_night_share"],
        "value",
        [
            str(window),
            f"{start_hour}:00–{end_hour}:59 (wrap)",
            total_watch,
            late_watch,
            f"{late_share:.2%}",
        ],
    )

    by_date = late.group("date").sort("date") if late.num_rows else Table().with_columns("note", ["No late-night watch events."])

    return {"summary": summary, "late_by_date": by_date}


# -------------------------
# NEW: Doomscroll indicator
# -------------------------

def tiktok_doomscroll_indicator(
    t: Table,
    window: str | None = "all",
    late_start: int = 23,
    late_end: int = 4,
    session_gap_minutes: int = 20,
    top_n_days: int = 10,
):
    """
    Doomscroll indicator (TikTok-only):
    Flags heavy days by combining:
      - high watch volume (events per day)
      - late-night share
      - long sessions (approx) using gap threshold

    Works with beginner-friendly outputs.

    Returns dict:
      - summary (overall)
      - day_scores (top days)
    """
    t2 = _filter_window_by_latest_date(t, window)
    watch = t2.where("action_type", "watch")

    if watch.num_rows == 0:
        return {"summary": Table().with_columns("note", ["No watch events found."])}

    # Ensure timestamp_dt exists (it does from add_basic_time_columns)
    if "timestamp_dt" not in watch.labels:
        watch = add_basic_time_columns(watch)

    # Build per-day counts
    by_day = watch.group("date").sort("count", descending=True)

    # Helper: late-night events per day
    late = watch.where("hour", lambda h: (h is not None) and (h >= late_start or h <= late_end))
    late_by_day = late.group("date") if late.num_rows else Table().with_columns("date", [], "count", [])

    # Build a lookup dict for late counts
    late_map = {}
    if late_by_day.num_rows:
        for d, c in zip(late_by_day.column("date"), late_by_day.column("count")):
            late_map[d] = c

    # Approx session count per day using time gaps
    # Session count = 1 + number of gaps > session_gap_minutes
    gap_seconds = session_gap_minutes * 60

    def session_count_for_date(day):
        day_tbl = watch.where("date", day).sort("timestamp_dt")
        dts = list(day_tbl.column("timestamp_dt"))
        if not dts:
            return 0
        sessions = 1
        for i in range(1, len(dts)):
            if (dts[i] - dts[i-1]).total_seconds() > gap_seconds:
                sessions += 1
        return sessions

    # Compute day-level doom score
    # score = watches + 2*(late_night_watches) + 10*(sessions>=3) as a simple heuristic
    dates = list(by_day.column("date"))
    counts = list(by_day.column("count"))

    rows = []
    for d, cnt in zip(dates, counts):
        late_cnt = late_map.get(d, 0)
        sessions = session_count_for_date(d)

        score = cnt + 2 * late_cnt + (10 if sessions >= 3 else 0)

        rows.append(
            {
                "date": d,
                "watch_events": cnt,
                "late_night_watch_events": late_cnt,
                "sessions_est": sessions,
                "doomscroll_score": score,
            }
        )

    day_scores = Table().with_columns(
        "date", [r["date"] for r in rows],
        "watch_events", [r["watch_events"] for r in rows],
        "late_night_watch_events", [r["late_night_watch_events"] for r in rows],
        "sessions_est", [r["sessions_est"] for r in rows],
        "doomscroll_score", [r["doomscroll_score"] for r in rows],
    ).sort("doomscroll_score", descending=True)

    # top days
    top_days = day_scores.take(range(min(top_n_days, day_scores.num_rows))) if day_scores.num_rows else day_scores

    overall = Table().with_columns(
        "metric",
        ["window", "total_watch_events", "unique_watch_days", "session_gap_minutes", "late_hours"],
        "value",
        [
            str(window),
            watch.num_rows,
            len(set(watch.column("date"))),
            session_gap_minutes,
            f"{late_start}:00–{late_end}:59 (wrap)",
        ],
    )

    return {"summary": overall, "day_scores": top_days}