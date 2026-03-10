import pandas as pd
from .parsers import watch_history, likes, searches, comments, shares, reposts

def tiktok_events(path: str, tz: str = "America/New_York") -> pd.DataFrame:
    parts = [
        watch_history(path, tz),
        likes(path, tz),
        searches(path, tz),
        comments(path, tz),
        shares(path, tz),
        reposts(path, tz),
    ]
    df = pd.concat(parts, ignore_index=True)
    df = df.dropna(subset=["timestamp_ny"]).sort_values("timestamp_ny")
    return df
