import pandas as pd
from .common import load_json, safe_get, parse_utc_string_to_local, finalize, NY_TZ_DEFAULT

def searches(path: str, tz: str = NY_TZ_DEFAULT) -> pd.DataFrame:
    data = load_json(path)
    items = safe_get(data, ["Your Activity", "Searches", "SearchList"]) or []

    rows = []
    for it in items:
        if not isinstance(it, dict):
            continue
        ts = it.get("Date") or it.get("date")
        dt = parse_utc_string_to_local(ts, tz)
        if dt is None:
            continue

        term = it.get("SearchTerm") or it.get("search_term") or it.get("Search") or it.get("Term") or pd.NA

        rows.append({
            "timestamp_ny": dt,
            "date": dt.date(),
            "hour": dt.hour,
            "event_type": "search",
            "source_path": "Your Activity.Searches.SearchList",
            "url": pd.NA,
            "text": term,
        })

    return finalize(pd.DataFrame(rows))
