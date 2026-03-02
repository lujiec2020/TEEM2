import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

def _rows_to_table(rows):
    """
    Convert rows into a datascience.Table if available,
    otherwise return a pandas.DataFrame.
    """
    try:
        from datascience import Table
    except ImportError:
        import pandas as pd
        return pd.DataFrame(rows)

    if not rows:
        return Table().with_columns(
            "object_type", [],
            "action_type", [],
            "actor", [],
            "target", [],
            "value", [],
            "timestamp", [],
            "timestamp_unix", [],
            "source_path", [],
        )

    cols = ["object_type","action_type","actor","target","value","timestamp","timestamp_unix","source_path"]
    data = {c: [r.get(c, "") for r in rows] for c in cols}

    return Table().with_columns(
        "object_type", data["object_type"],
        "action_type", data["action_type"],
        "actor", data["actor"],
        "target", data["target"],
        "value", data["value"],
        "timestamp", data["timestamp"],
        "timestamp_unix", data["timestamp_unix"],
        "source_path", data["source_path"],
    )

def _parse_utc_string_to_local(ts_str: str, tz: str):
    """
    TikTok JSON timestamps look like 'YYYY-MM-DD HH:MM:SS' and are typically UTC.
    Convert to local timezone and return formatted string + datetime.
    """
    if not ts_str:
        return None, None
    try:
        dt_utc = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo("UTC"))
    except ValueError:
        return None, None

    dt_local = dt_utc.astimezone(ZoneInfo(tz))
    formatted = dt_local.strftime("%Y-%m-%d %I:%M:%S %p %Z")
    return formatted, dt_local

def tiktok_events(path: str, tz: str = "America/New_York"):
    """
    Parse TikTok user_data_tiktok.json into a single normalized events table.
    Returns: datascience.Table if installed, otherwise pandas.DataFrame
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []
    actor = "self"

    # WATCH HISTORY
    watch_list = data.get("Your Activity", {}).get("Watch History", {}).get("VideoList", [])
    for it in watch_list:
        ts = it.get("Date")
        formatted, dt_local = _parse_utc_string_to_local(ts, tz)
        if not formatted:
            continue
        rows.append({
            "object_type": "video",
            "action_type": "watch",
            "actor": actor,
            "target": it.get("Link", "") or "",
            "value": "",
            "timestamp": formatted,
            "timestamp_unix": "",
            "source_path": "Your Activity.Watch History.VideoList",
        })

    # LIKES
    like_list = data.get("Likes and Favorites", {}).get("Like List", {}).get("ItemFavoriteList", [])
    for it in like_list:
        ts = it.get("date") or it.get("Date")
        formatted, _ = _parse_utc_string_to_local(ts, tz)
        if not formatted:
            continue
        rows.append({
            "object_type": "video",
            "action_type": "like",
            "actor": actor,
            "target": it.get("link", "") or it.get("Link", "") or "",
            "value": "",
            "timestamp": formatted,
            "timestamp_unix": "",
            "source_path": "Likes and Favorites.Like List.ItemFavoriteList",
        })

    # SEARCHES
    search_list = data.get("Your Activity", {}).get("Searches", {}).get("SearchList", [])
    for it in search_list:
        ts = it.get("Date") or it.get("date")
        formatted, _ = _parse_utc_string_to_local(ts, tz)
        if not formatted:
            continue
        # Find a likely search-term field (varies)
        term = it.get("SearchTerm") or it.get("search_term") or it.get("Search") or it.get("Term") or ""
        rows.append({
            "object_type": "search",
            "action_type": "search",
            "actor": actor,
            "target": "",
            "value": term,
            "timestamp": formatted,
            "timestamp_unix": "",
            "source_path": "Your Activity.Searches.SearchList",
        })

    # COMMENTS
    comment_list = data.get("Comment", {}).get("Comments", {}).get("CommentsList", [])
    for it in comment_list:
        ts = it.get("date") or it.get("Date")
        formatted, _ = _parse_utc_string_to_local(ts, tz)
        if not formatted:
            continue
        rows.append({
            "object_type": "comment",
            "action_type": "comment",
            "actor": actor,
            "target": it.get("url", "") or it.get("Link", "") or "",
            "value": it.get("comment", "") or it.get("Content", "") or "",
            "timestamp": formatted,
            "timestamp_unix": "",
            "source_path": "Comment.Comments.CommentsList",
        })

    # SHARES (if exists)
    share_list = data.get("Your Activity", {}).get("Share History", {}).get("ShareHistoryList", [])
    for it in share_list:
        ts = it.get("Date") or it.get("date")
        formatted, _ = _parse_utc_string_to_local(ts, tz)
        if not formatted:
            continue
        rows.append({
            "object_type": "share",
            "action_type": "share",
            "actor": actor,
            "target": it.get("url", "") or it.get("Link", "") or "",
            "value": it.get("Method", "") or "",
            "timestamp": formatted,
            "timestamp_unix": "",
            "source_path": "Your Activity.Share History.ShareHistoryList",
        })

    # REPOSTS (if exists)
    repost_list = data.get("Your Activity", {}).get("Reposts", {}).get("RepostList", [])
    for it in repost_list:
        ts = it.get("Date") or it.get("date")
        formatted, _ = _parse_utc_string_to_local(ts, tz)
        if not formatted:
            continue
        rows.append({
            "object_type": "repost",
            "action_type": "repost",
            "actor": actor,
            "target": it.get("url", "") or it.get("Link", "") or "",
            "value": "",
            "timestamp": formatted,
            "timestamp_unix": "",
            "source_path": "Your Activity.Reposts.RepostList",
        })

    return _rows_to_table(rows)