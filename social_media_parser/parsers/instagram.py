import json
from pathlib import Path

from social_media_parser.utils import rows_to_table, unix_to_local_dt, format_timestamp
from social_media_parser.time_features import EventTable


def parse_instagram(path: str = ".", tz: str = "America/New_York") -> EventTable:
    """
    Parse Instagram export data into a unified event table.

    This function scans a directory (and its subdirectories) for Instagram
    JSON export files and extracts structured activity such as story likes,
    poll responses, and comments on posts and reels.

    Parameters
    ----------
    path : str, optional
        Path to the folder containing Instagram JSON files (default is current directory).
    tz : str, optional
        Timezone used to convert Unix timestamps into human-readable datetime values
        (default is "America/New_York").

    Returns
    -------
    EventTable
        A structured table containing Instagram activity with standardized fields:
        object_type, action_type, username, target, value, and timestamps.

    Raises
    ------
    FileNotFoundError
        If the provided folder path does not exist or is not a directory.
    """
    # Convert input path string to a Path object for easier file handling
    folder = Path(path)

    if not folder.exists() or not folder.is_dir():
        raise FileNotFoundError(
            f"Folder not found: {folder}\n"
            "Please provide the folder containing your downloaded Instagram data."
        )

    rows = []

    # Recursively find all JSON files in the folder
    json_files = sorted(folder.rglob("*.json"))

    # Return empty table if no files are found
    if not json_files:
        return EventTable(rows_to_table([]))

    # Process each JSON file individually
    for fp in json_files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            # Skip files that cannot be read or parsed
            continue

        # ---------------------------
        # STORY ACTIVITY PROCESSING
        # ---------------------------
        if isinstance(data, dict):

            # Story likes
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

            # Story poll responses
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

                # Extract media target (e.g., post image/video URI)
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

    return EventTable(rows_to_table(rows))


# Compatibility for older code versions
instagram_events = parse_instagram
