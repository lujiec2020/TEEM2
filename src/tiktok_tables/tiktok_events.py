import json
from pathlib import Path
from datetime import datetime

from datascience import Table

from src.Tools.utils import tiktok_utc_string_to_timestamp, rows_to_table

DEFAULT_TZ = "America/New_York"
COLUMNS = ["platform", "object_type", "action_type", "username", "target", "value", "timestamp"]


def add_basic_time_columns(t):
    """
    Adds 'hour', 'weekday', and 'date' columns using the existing 'timestamp' string.

    Works even if the timestamp ends with EST/EDT by ignoring the last token.
    Example timestamp: '2019-07-15 10:23:42 PM EDT'
    """

    def to_dt(ts):
        # drop timezone token (EST/EDT/etc.)
        ts_no_tz = " ".join(str(ts).split(" ")[:-1])
        return datetime.strptime(ts_no_tz, "%Y-%m-%d %I:%M:%S %p")

    t = t.with_column("timestamp_dt", t.apply(to_dt, "timestamp"))
    t = t.with_column("hour", t.apply(lambda d: d.hour, "timestamp_dt"))
    t = t.with_column("weekday", t.apply(lambda d: d.strftime("%A"), "timestamp_dt"))
    t = t.with_column("date", t.apply(lambda d: d.date(), "timestamp_dt"))
    return t


def tiktok_events(json_path: str, tz: str = DEFAULT_TZ):
    """
    Parse TikTok user_data_tiktok.json into a single beginner-friendly events table with columns:
      platform, object_type, action_type, username, target, value, timestamp

    Timezone changes: call again with a different tz, e.g. tz="America/Los_Angeles".
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


def tiktok_watch_summary(t):
    """
    Beginner-friendly TikTok-only summary.
    Input: datascience.Table from tiktok_events(...)
    Output: dict of small tables students can show/plot.
    """
    watch = t.where("action_type", "watch")

    total = Table().with_columns(
        "metric", ["total_watch_events"],
        "value", [watch.num_rows]
    )

    if "hour" in watch.labels:
        by_hour = watch.group("hour").sort("count", descending=True)
    else:
        by_hour = Table().with_columns("note", ["No 'hour' column yet."])

    if "weekday" in watch.labels:
        by_weekday = watch.group("weekday").sort("count", descending=True)
    else:
        by_weekday = Table().with_columns("note", ["No 'weekday' column yet."])

    if "date" in watch.labels:
        by_date = watch.group("date").sort("date")
    else:
        by_date = Table().with_columns("note", ["No 'date' column yet."])

    return {
        "total": total,
        "by_hour": by_hour,
        "by_weekday": by_weekday,
        "by_date": by_date
    }