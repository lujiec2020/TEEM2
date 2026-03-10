from datascience import Table

# Instagram side
from social_media_parser.parsers.instagram import instagram_events

# TikTok side (use the same import style students will use in notebooks)
from src.tiktok_tables.tiktok_events import tiktok_events

from datetime import datetime, timedelta

FINAL_COLS = ["platform", "object_type", "action_type", "username", "target", "value", "timestamp"]

# clearer window names
_WINDOW_DAYS = {
    "1_week": 7,
    "1_month": 30,
    "3_month": 90,
    "6_month": 180,
    "1_year": 365,
}


def _ensure_column(t: Table, col: str, default=""):
    """If a column is missing, add it with a default value."""
    if col not in t.labels:
        t = t.with_column(col, [default] * t.num_rows)
    return t


def _to_final_schema(t: Table, platform_name: str) -> Table:
    """
    Standardize any incoming table to:
    platform, object_type, action_type, username, target, value, timestamp
    """
    # Ensure platform column
    t = _ensure_column(t, "platform", platform_name)

    # TikTok uses actor -> rename to username
    if "actor" in t.labels and "username" not in t.labels:
        t = t.relabel("actor", "username")

    # Ensure username exists
    t = _ensure_column(t, "username", "")

    # Ensure the rest exist
    for c in ["object_type", "action_type", "target", "value", "timestamp"]:
        t = _ensure_column(t, c, "")

    # Select only the final columns in the right order
    return t.select(*FINAL_COLS)


def _parse_timestamp_to_dt(ts: str):
    """
    Convert 'YYYY-MM-DD HH:MM:SS AM/PM EST/EDT' -> datetime
    We ignore the final timezone token because it can be EST or EDT.
    """
    if ts is None:
        return None
    ts = str(ts).strip()
    if not ts:
        return None

    parts = ts.split(" ")
    if len(parts) < 3:
        return None

    ts_no_tz = " ".join(parts[:-1])  # drop EST/EDT
    try:
        return datetime.strptime(ts_no_tz, "%Y-%m-%d %I:%M:%S %p")
    except Exception:
        return None


def filter_by_time_window(t: Table, window: str | None):
    """
    Filter table to only keep rows within the last window,
    relative to the *latest timestamp in the table*.

    window options: None (no filter), "1_week", "1_month", "3_month", "6_month", "1_year"
    """
    if window is None:
        return t

    window = str(window).lower().strip()
    if window not in _WINDOW_DAYS:
        raise ValueError(f"window must be one of {list(_WINDOW_DAYS.keys())} or None")

    # Parse timestamps into datetimes (temporary)
    dt_list = t.apply(_parse_timestamp_to_dt, "timestamp")

    valid_dts = [d for d in dt_list if d is not None]
    if not valid_dts:
        return t  # nothing to filter on

    latest_dt = max(valid_dts)
    cutoff = latest_dt - timedelta(days=_WINDOW_DAYS[window])

    # add temp column, filter, then remove
    t2 = t.with_column("_dt_tmp", dt_list)
    t2 = t2.where("_dt_tmp", lambda d: (d is not None) and (d >= cutoff))

    keep_cols = [c for c in t2.labels if c != "_dt_tmp"]
    return t2.select(*keep_cols)


def social_media_events(
    instagram_folder: str,
    tiktok_json: str,
    tz: str = "America/New_York",
    window: str | None = None,
) -> Table:
    """
    One-call combined function.

    Returns ONE datascience Table with columns:
      platform, object_type, action_type, username, target, value, timestamp

    Optional filtering:
      window = "1_week" | "1_month" | "3_month" | "6_month" | "1_year" | None
    """
    insta_event_table = instagram_events(instagram_folder, tz)  # EventTable wrapper
    insta = insta_event_table.table                              # unwrap to Table

    tiktok = tiktok_events(tiktok_json, tz)                      # Table

    insta_final = _to_final_schema(insta, "instagram")
    tiktok_final = _to_final_schema(tiktok, "tiktok")

    combined = insta_final.append(tiktok_final)

    # Sort by timestamp string if it starts with YYYY-MM-DD (safe for your format)
    if "timestamp" in combined.labels:
        try:
            combined = combined.sort("timestamp")
        except Exception:
            pass

    # Apply optional time window filter
    combined = filter_by_time_window(combined, window)

    return combined


def add_basic_time_columns(t: Table) -> Table:
    """
    Adds: timestamp_dt, hour, weekday, date
    Keeps beginner-friendly columns so students can group easily.
    """
    t = t.with_column("timestamp_dt", t.apply(_parse_timestamp_to_dt, "timestamp"))
    t = t.with_column("hour", t.apply(lambda d: d.hour if d else None, "timestamp_dt"))
    t = t.with_column("weekday", t.apply(lambda d: d.strftime("%A") if d else None, "timestamp_dt"))
    t = t.with_column("date", t.apply(lambda d: d.date() if d else None, "timestamp_dt"))
    return t


def events_by_hour(t: Table) -> Table:
    """Return counts of events by hour (0–23)."""
    if "hour" not in t.labels:
        t = add_basic_time_columns(t)
    return t.group("hour").sort("count", descending=True)


def events_by_weekday(t: Table) -> Table:
    """Return counts of events by weekday."""
    if "weekday" not in t.labels:
        t = add_basic_time_columns(t)
    return t.group("weekday").sort("count", descending=True)


def events_by_date(t: Table) -> Table:
    """Return counts of events by date."""
    if "date" not in t.labels:
        t = add_basic_time_columns(t)
    return t.group("date").sort("date")