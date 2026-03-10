import json
from pathlib import Path
import pandas as pd

NY_TZ = "America/New_York"


def to_ny(ts):
    """
    Convert a timestamp (single value OR pandas Series) to New York time.
    TikTok takeout timestamps are typically UTC.
    """
    dt = pd.to_datetime(ts, utc=True, errors="coerce")

    # Series case (e.g., column)
    if isinstance(dt, pd.Series):
        return dt.dt.tz_convert(NY_TZ)

    # Single value case
    if pd.isna(dt):
        return pd.NaT
    return dt.tz_convert(NY_TZ)


def safe_get(d, path):
    """Safely walk nested dict keys. Returns None if anything is missing."""
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def pick_ts_field(items, preferred):
    """Pick a timestamp field that exists in the first item dict."""
    if not items or not isinstance(items, list) or not isinstance(items[0], dict):
        return None
    keys = list(items[0].keys())

    for f in preferred:
        if f in keys:
            return f

    # fallback: any key containing date/time
    for k in keys:
        lk = str(k).lower()
        if "date" in lk or "time" in lk or "timestamp" in lk:
            return k

    return None


def add_events(rows, items, event_type, ts_field, source_path, keep_fields=None):
    """
    Normalize a list of dict items into an event table.
    Adds: timestamp_ny, date, hour, event_type, source_path + selected original fields.
    """
    keep_fields = keep_fields or []
    if not items or not isinstance(items, list) or not ts_field:
        return

    for it in items:
        if not isinstance(it, dict):
            continue

        ts = it.get(ts_field)
        dt = to_ny(ts)
        if pd.isna(dt):
            continue

        row = {
            "timestamp_ny": dt,
            "date": dt.date(),
            "hour": dt.hour,
            "event_type": event_type,
            "source_path": source_path,
        }

        for f in keep_fields:
            if f in it:
                row[f] = it.get(f)

        rows.append(row)


def main():
    in_path = Path("data/user_data_tiktok.json")
    out_dir = Path("output")
    out_dir.mkdir(exist_ok=True)

    with open(in_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []

    # 1) Watch History
    watch = safe_get(data, ["Your Activity", "Watch History", "VideoList"])
    if watch:
        ts_field = pick_ts_field(watch, ["Date", "date", "Time", "time", "Timestamp"])
        keep = [c for c in watch[0].keys() if c != ts_field]
        add_events(
            rows, watch, "watch", ts_field,
            source_path="Your Activity.Watch History.VideoList",
            keep_fields=keep
        )

    # 2) Likes
    likes = safe_get(data, ["Likes and Favorites", "Like List", "ItemFavoriteList"])
    if likes:
        ts_field = pick_ts_field(likes, ["date", "Date", "Time", "time", "Timestamp"])
        keep = [c for c in likes[0].keys() if c != ts_field]
        add_events(
            rows, likes, "like", ts_field,
            source_path="Likes and Favorites.Like List.ItemFavoriteList",
            keep_fields=keep
        )

    # 3) Searches
    searches = safe_get(data, ["Your Activity", "Searches", "SearchList"])
    if searches:
        ts_field = pick_ts_field(searches, ["Date", "date", "Time", "time", "Timestamp"])
        keep = [c for c in searches[0].keys() if c != ts_field]
        add_events(
            rows, searches, "search", ts_field,
            source_path="Your Activity.Searches.SearchList",
            keep_fields=keep
        )

    # 4) Comments
    comments = safe_get(data, ["Comment", "Comments", "CommentsList"])
    if comments:
        ts_field = pick_ts_field(comments, ["date", "Date", "Time", "time", "Timestamp"])
        keep = [c for c in comments[0].keys() if c != ts_field]
        add_events(
            rows, comments, "comment", ts_field,
            source_path="Comment.Comments.CommentsList",
            keep_fields=keep
        )

    # 5) Shares (optional)
    shares = safe_get(data, ["Your Activity", "Share History", "ShareHistoryList"])
    if shares:
        ts_field = pick_ts_field(shares, ["Date", "date", "Time", "time", "Timestamp"])
        keep = [c for c in shares[0].keys() if c != ts_field]
        add_events(
            rows, shares, "share", ts_field,
            source_path="Your Activity.Share History.ShareHistoryList",
            keep_fields=keep
        )

    # 6) Reposts (optional)
    reposts = safe_get(data, ["Your Activity", "Reposts", "RepostList"])
    if reposts:
        ts_field = pick_ts_field(reposts, ["Date", "date", "Time", "time", "Timestamp"])
        keep = [c for c in reposts[0].keys() if c != ts_field]
        add_events(
            rows, reposts, "repost", ts_field,
            source_path="Your Activity.Reposts.RepostList",
            keep_fields=keep
        )

    df = pd.DataFrame(rows)

    if df.empty:
        print("No events extracted. Check your JSON paths/keys.")
        return

    df = df.sort_values("timestamp_ny")

    # Standardize common fields (helps later when graphing)
    # If a column exists, copy it into a standard name.
    if "Link" in df.columns and "link" not in df.columns:
        df["link"] = df["Link"]
    if "link" in df.columns and "link" not in df.columns:
        df["link"] = df["link"]
    if "Content" in df.columns and "content" not in df.columns:
        df["content"] = df["Content"]

    out_path = out_dir / "events.csv"
    df.to_csv(out_path, index=False)

    print("Wrote:", out_path, "rows:", len(df))
    print("Event types:", sorted(df["event_type"].unique().tolist()))


if __name__ == "__main__":
    main()