import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd

NY_TZ_DEFAULT = "America/New_York"
STANDARD_COLS = ["timestamp_ny", "date", "hour", "event_type", "source_path", "url", "text"]

def load_json(path: str) -> dict:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def safe_get(d: dict, path: list):
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur

def parse_utc_string_to_local(ts_str: str, tz: str = NY_TZ_DEFAULT):
    if not ts_str:
        return None
    try:
        dt_utc = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo("UTC"))
        return dt_utc.astimezone(ZoneInfo(tz))
    except Exception:
        return None

def finalize(df: pd.DataFrame) -> pd.DataFrame:
    for c in STANDARD_COLS:
        if c not in df.columns:
            df[c] = pd.NA
    return df[STANDARD_COLS]
