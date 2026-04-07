import json
from pathlib import Path

from social_media_parser.utils import (
    rows_to_table,
    unix_to_local_dt,
    format_timestamp,
    index_by_active_day,  # 👈 NEW IMPORT
)
from social_media_parser.time_features import EventTable


def parse_instagram(path: str = ".", tz: str = "America/New_York") -> EventTable:
    """
    Parse Instagram export data into a unified event table.

    This function scans a directory (and its subdirectories) for Instagram
    JSON export files and extracts structured activity such as story likes,
    poll responses, and comments on posts and reels.
    """
    folder = Path(path)

    if not folder.exists() or not folder.is_dir():
        raise FileNotFoundError(
            f"Folder not found: {folder}\n"
            "Please provide the folder containing your downloaded Instagram data."
        )

    rows = []
    json_files = sorted(folder.rglob("*.json"))

    if not json_files:
        return EventTable(rows_to_table([]))

    for fp in json_files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        # ---------------------------
        # STORY ACTIVITY PROCESSING
        # ---------------------------
        if isinstance(data, dict):

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
                        except (TypeError, ValueError):
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
                        except (TypeError, ValueError):
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

        # ---------------------------
        # REEL COMMENTS PROCESSING
        # ---------------------------
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
                except (TypeError, ValueError):
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

        # ---------------------------
        # POST COMMENTS PROCESSING
        # ---------------------------
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
                except (TypeError, ValueError):
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
    # Sort chronologically (oldest → newest)
    rows.sort(key=lambda r: r["timestamp_unix"])
    # Add relative day indexing
    rows = index_by_active_day(rows)

    return EventTable(rows_to_table(rows))


# Compatibility for older code versions
instagram_events = parse_instagram
