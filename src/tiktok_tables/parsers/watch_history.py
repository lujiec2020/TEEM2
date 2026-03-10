import pandas as pd
from .common import load_json, safe_get, parse_utc_string_to_local, finalize, NY_TZ_DEFAULT

def watch_history(path: str, tz: str = NY_TZ_DEFAULT) -> pd.DataFrame:
    data = load_json(path)
    items = safe_get(data, ["Your Activity", "Watch History", "VideoList"]) or []

    rows = []
    for it in items:
        if not isinstance(it, dict):
            continue
        dt = parse_utc_string_to_local(it.get("Date"), tz)
        if dt is None:
            continue
        rows.append({
            "timestamp_ny": dt,
            "date": dt.date(),
            "hour": dt.hour,
            "event_type": "watch",
            "source_path": "Your Activity.Watch History.VideoList",
            "url": it.get("Link") or it.get("link") or it.get("url"),
            "text": pd.NA,
        })

    return finalize(pd.DataFrame(rows))
