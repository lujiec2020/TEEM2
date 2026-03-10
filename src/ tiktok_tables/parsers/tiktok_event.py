import json
from pathlib import Path

from src.Tools.utils import (
    rows_to_table,
    tiktok_utc_string_to_local_dt,
    format_timestamp,
    to_unix_seconds,
)

DEFAULT_TZ = "America/New_York"


def tiktok_events(json_path: str, tz: str = DEFAULT_TZ):
    """
    TikTok -> Instagram-style events table:
    platform, object_type, action_type, actor, target, value, timestamp_dt, timestamp, timestamp_unix
    """
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []
    actor = "self"

    def add(object_type, action_type, ts_str, target="", value=""):
        if not ts_str:
            return
        try:
            dt_local = tiktok_utc_string_to_local_dt(ts_str, tz)
        except Exception:
            return

        rows.append(
            {
                "platform": "tiktok",
                "object_type": object_type,
                "action_type": action_type,
                "actor": actor,
                "target": target or "",
                "value": value or "",
                "timestamp_dt": dt_local,
                "timestamp": format_timestamp(dt_local),
                "timestamp_unix": to_unix_seconds(dt_local),
            }
        )

    # Watch History
    for it in data.get("Your Activity", {}).get("Watch History", {}).get("VideoList", []) or []:
        add("video", "watch", it.get("Date"), target=(it.get("Link") or it.get("link") or it.get("url") or ""))

    # Likes
    for it in data.get("Likes and Favorites", {}).get("Like List", {}).get("ItemFavoriteList", []) or []:
        add("video", "like", it.get("date") or it.get("Date"),
            target=(it.get("link") or it.get("Link") or it.get("url") or ""))

    # Searches
    for it in data.get("Your Activity", {}).get("Searches", {}).get("SearchList", []) or []:
        term = it.get("SearchTerm") or it.get("Search") or it.get("Term") or ""
        add("search", "search", it.get("Date") or it.get("date"), value=term)

    # Comments
    for it in data.get("Comment", {}).get("Comments", {}).get("CommentsList", []) or []:
        txt = it.get("comment") or it.get("Content") or it.get("content") or ""
        url = it.get("url") or it.get("Link") or it.get("link") or ""
        add("comment", "comment", it.get("date") or it.get("Date"), target=url, value=txt)

    # Shares
    for it in data.get("Your Activity", {}).get("Share History", {}).get("ShareHistoryList", []) or []:
        url = it.get("url") or it.get("Link") or it.get("SharedContent") or it.get("link") or ""
        method = it.get("Method") or ""
        add("share", "share", it.get("Date") or it.get("date"), target=url, value=method)

    # Reposts
    for it in data.get("Your Activity", {}).get("Reposts", {}).get("RepostList", []) or []:
        url = it.get("url") or it.get("Link") or it.get("link") or ""
        add("video", "repost", it.get("Date") or it.get("date"), target=url)

    return rows_to_table(rows)