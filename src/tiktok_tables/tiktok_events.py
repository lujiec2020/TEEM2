import json
from pathlib import Path

from src.Tools.utils import tiktok_utc_string_to_timestamp, rows_to_table

DEFAULT_TZ = "America/New_York"
COLUMNS = ["platform", "object_type", "action_type", "actor", "target", "value", "timestamp"]


def tiktok_events(json_path: str, tz: str = DEFAULT_TZ):
    """
    Parse TikTok user_data_tiktok.json into a single beginner-friendly events table with columns:
    platform, object_type, action_type, actor, target, value, timestamp

    Timezone changes: call again with a different tz, e.g. tz="America/Los_Angeles".
    """
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []
    actor = "self"

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
                "actor": actor,
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

    return rows_to_table(rows, columns=COLUMNS)