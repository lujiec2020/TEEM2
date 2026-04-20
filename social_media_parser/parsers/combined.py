from datascience import Table

from social_media_parser.parsers.instagram import instagram_events
from src.tiktok_tables.tiktok_events import tiktok_events

FINAL_COLS = ["platform", "object_type", "action_type", "username", "target", "value", "timestamp"]


def _ensure_column(t: Table, col: str, default=""):
    if col not in t.labels:
        t = t.with_column(col, [default] * t.num_rows)
    return t


def _to_final_schema(t: Table, platform_name: str) -> Table:
    t = _ensure_column(t, "platform", platform_name)

    # Instagram already uses username; TikTok uses username too (now)
    t = _ensure_column(t, "username", "")

    for c in ["object_type", "action_type", "target", "value", "timestamp"]:
        t = _ensure_column(t, c, "")

    return t.select(*FINAL_COLS)


def social_media_events(
    instagram_folder: str,
    tiktok_json: str,
    tz: str = "America/New_York",
    start_date: str | None = None,
    end_date: str | None = None,
) -> Table:
    """
    One-call function:
      - reads Instagram takeout folder
      - reads TikTok user_data_tiktok.json
      - returns ONE combined Table in a consistent schema

    Optional date range filter:
      start_date="12-16-2025", end_date="1-8-2026"
    """
    insta = instagram_events(instagram_folder, tz=tz, start_date=start_date, end_date=end_date).table
    tiktok = tiktok_events(tiktok_json, tz=tz, start_date=start_date, end_date=end_date)

    insta_final = _to_final_schema(insta, "instagram")
    tiktok_final = _to_final_schema(tiktok, "tiktok")

    combined = insta_final.append(tiktok_final)

    if "timestamp" in combined.labels:
        try:
            combined = combined.sort("timestamp")
        except Exception:
            pass

    return combined


# -------------------------
# Quick time group helpers
# -------------------------

from datetime import datetime


def _parse_timestamp_to_dt(ts: str):
    if ts is None:
        return None
    ts = str(ts).strip()
    parts = ts.split(" ")
    if len(parts) < 3:
        return None
    ts_no_tz = " ".join(parts[:-1])
    try:
        return datetime.strptime(ts_no_tz, "%Y-%m-%d %I:%M:%S %p")
    except Exception:
        return None


def add_basic_time_columns(t: Table) -> Table:
    t = t.with_column("timestamp_dt", t.apply(_parse_timestamp_to_dt, "timestamp"))
    t = t.with_column("hour", t.apply(lambda d: d.hour if d else None, "timestamp_dt"))
    t = t.with_column("weekday", t.apply(lambda d: d.strftime("%A") if d else None, "timestamp_dt"))
    t = t.with_column("date", t.apply(lambda d: d.date() if d else None, "timestamp_dt"))
    return t


def events_by_hour(t: Table) -> Table:
    if "hour" not in t.labels:
        t = add_basic_time_columns(t)
    return t.group("hour").sort("count", descending=True)


def events_by_weekday(t: Table) -> Table:
    if "weekday" not in t.labels:
        t = add_basic_time_columns(t)
    return t.group("weekday").sort("count", descending=True)


def events_by_date(t: Table) -> Table:
    if "date" not in t.labels:
        t = add_basic_time_columns(t)
    return t.group("date").sort("date")