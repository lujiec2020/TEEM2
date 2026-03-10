import pandas as pd
from .common import load_json, safe_get, parse_utc_string_to_local, finalize, NY_TZ_DEFAULT

def likes(path: str, tz: str = NY_TZ_DEFAULT) -> pd.DataFrame:
    data = load_json(path)
    items = safe_get(data, ["Likes and Favorites", "Like List", "ItemFavoriteList"]) or []

    rows = []
    for it in items:
        if not isinstance(it, dict):
            continue
        ts = it.get("date") or it.get("Date")
        dt = parse_utc_string_to_local(ts, tz)
        if dt is None:
            continue
        rows.append({
            "timestamp_ny": dt,
            "date": dt.date(),
            "hour": dt.hour,
            "event_type": "like",
            "source_path": "Likes and Favorites.Like List.ItemFavoriteList",
            "url": it.get("link") or it.get("Link") or it.get("url"),
            "text": pd.NA,
        })

    return finalize(pd.DataFrame(rows))
