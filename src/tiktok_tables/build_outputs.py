from pathlib import Path
from .tiktok_events import tiktok_events
from .parsers import watch_history, likes, searches, comments, shares, reposts

def main():
    in_path = "data/user_data_tiktok.json"
    out = Path("output")
    out.mkdir(exist_ok=True)

    watch_history(in_path).to_csv(out / "watch_history_clean.csv", index=False)
    likes(in_path).to_csv(out / "likes_clean.csv", index=False)
    searches(in_path).to_csv(out / "searches_clean.csv", index=False)
    comments(in_path).to_csv(out / "comments_clean.csv", index=False)
    shares(in_path).to_csv(out / "shares_clean.csv", index=False)
    reposts(in_path).to_csv(out / "reposts_clean.csv", index=False)

    all_events = tiktok_events(in_path)
    all_events.to_csv(out / "events_clean.csv", index=False)

    print("Wrote CSVs to output/")

if __name__ == "__main__":
    main()
