import pandas as pd
from .common import load_json, safe_get, parse_utc_string_to_local, finalize, NY_TZ_DEFAULT

def shares(path: str, tz: str = NY_TZ_DEFAULT) -> pd.DataFrame:
    data = load_json(path)
    items = safe_get(data, ["Your Activity", "Share History", "ShareHistoryList"]) or []

    rows = []
    for it in items:
        if not isinstance(it, dict):
            continue
        ts = it.get("Date") or it.get("date")
        dt = parse_utc_string_to_local(ts, tz)
        if dt is None:
            continue

        url = it.get("url") or it.get("Link") or it.get("link") or it.get("SharedContent") or pd.NA
        method = it.get("Method") or pd.NA

        rows.append({
            "timestamp_ny": dt,
            "date": dt.date(),
            "hour": dt.hour,
            "event_type": "share",
            "source_path": "Your Activity.Share History.ShareHistoryList",
            "url": url,
            "text": method,
        })

    return finalize(pd.DataFrame(rows))
