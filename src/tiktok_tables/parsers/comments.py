import pandas as pd
from .common import load_json, safe_get, parse_utc_string_to_local, finalize, NY_TZ_DEFAULT

def comments(path: str, tz: str = NY_TZ_DEFAULT) -> pd.DataFrame:
    data = load_json(path)
    items = safe_get(data, ["Comment", "Comments", "CommentsList"]) or []

    rows = []
    for it in items:
        if not isinstance(it, dict):
            continue
        ts = it.get("date") or it.get("Date")
        dt = parse_utc_string_to_local(ts, tz)
        if dt is None:
            continue

        text = it.get("comment") or it.get("Content") or it.get("content") or pd.NA
        url = it.get("url") or it.get("Link") or it.get("link") or pd.NA

        rows.append({
            "timestamp_ny": dt,
            "date": dt.date(),
            "hour": dt.hour,
            "event_type": "comment",
            "source_path": "Comment.Comments.CommentsList",
            "url": url,
            "text": text,
        })

    return finalize(pd.DataFrame(rows))
