from pathlib import Path
from datascience import Table

from social_media_parser.parsers.instagram import instagram_events
from src.tiktok_tables.tiktok_events import tiktok_events

FINAL_COLS = ["platform", "object_type", "action_type", "username", "target", "value", "timestamp"]


# -------------------------
# Beginner-friendly errors
# -------------------------

class StudentInputError(Exception):
    pass


def _raise(msg: str):
    raise StudentInputError("⚠️ " + msg)


def _ensure_column(t: Table, col: str, default=""):
    if col not in t.labels:
        t = t.with_column(col, [default] * t.num_rows)
    return t


def _to_final_schema(t: Table, platform_name: str) -> Table:
    t = _ensure_column(t, "platform", platform_name)

    # support old TikTok actor name if it ever appears
    if "actor" in t.labels and "username" not in t.labels:
        t = t.relabel("actor", "username")

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
    Combined Instagram + TikTok in one Table (final schema).

    Optional date range:
      start_date="12-16-2025", end_date="1-8-2026"
    """
    ig_path = Path(instagram_folder)
    tk_path = Path(tiktok_json)

    if not ig_path.exists() or not ig_path.is_dir():
        _raise(
            f"Instagram folder not found: {ig_path}\n"
            "Fix: pass the folder containing Instagram JSON files (example: 'data')."
        )

    if not tk_path.exists():
        _raise(
            f"TikTok JSON not found: {tk_path}\n"
            "Fix: put your TikTok file in data/ and call:\n"
            "  social_media_events('data', 'data/user_data_tiktok.json')"
        )

    try:
        insta = instagram_events(instagram_folder, tz=tz, start_date=start_date, end_date=end_date).table
    except Exception as e:
        _raise(
            "Instagram parsing failed.\n"
            f"Fix: check your Instagram export files in '{instagram_folder}'.\n"
            f"Details: {e}"
        )

    try:
        tik = tiktok_events(tiktok_json, tz=tz, start_date=start_date, end_date=end_date)
    except Exception as e:
        _raise(
            "TikTok parsing failed.\n"
            f"Fix: check your TikTok file path and date format.\n"
            f"Details: {e}"
        )

    insta_final = _to_final_schema(insta, "instagram")
    tik_final = _to_final_schema(tik, "tiktok")

    combined = insta_final.append(tik_final)

    try:
        combined = combined.sort("timestamp")
    except Exception:
        pass

    return combined