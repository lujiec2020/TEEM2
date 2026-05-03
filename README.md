# Social Media Data Parser
This project converts raw Instagram and TikTok data exports into a unified, structured event dataset for analysis.

It standardizes both platforms into a consistent schema so users can:

- explore activity patterns
- analyze usage over time
- compare behavioral trends across platforms

All outputs are returned as `datascience.Table` objects.

## Installation
Install Python 3.9+ or ensure it is already installed

Install the package directly from GitHub:
```
pip install git+https://github.com/lujiec2020/TEEM2.git
```
Install Dependencies 
```
pip install datascience
pip install pytz
```
## Input Data
This project uses official data exports:

- Instagram export (JSON files inside a folder) 

- TikTok export (user_data_tiktok.json)

- Place them in:
```
data/
 ├── instagram_data/
 └── tiktok_data/
      └── user_data_tiktok.json
```
### Quick Start
```
from social_media_functions.parse_metadata import social_media_events

t = social_media_events(
    instagram_folder="data/instagram_data",
    tiktok_json="data/tiktok_data/user_data_tiktok.json"
)

t.show(5)
```

## Main Functions

### `parse_metadata()`
Parses Instagram export data into a structured event table.
```
from social_media_functions.parse_metadata import parse_metadata

ig = parse_metadata("data/instagram_data")
ig.show(5)

```
Output: Table of Instagram activity (e.g., story likes, interactions, timestamps).

<img width="664" height="389" alt="Screenshot 2026-05-01 at 1 32 42 AM" src="https://github.com/user-attachments/assets/034529a5-5118-4d52-9582-15672697697a" />

### `tiktok_events()`
Parses TikTok JSON export into structured events.

```
from social_media_functions.parse_metadata import tiktok_events

tt = tiktok_events("data/tiktok_data/user_data_tiktok.json")
tt.show(5)
```
Output: Table of TikTok activity (e.g., watch history and engagement events with timestamps).

<img width="661" height="384" alt="Screenshot 2026-05-01 at 1 33 55 AM" src="https://github.com/user-attachments/assets/e317f89f-3c8c-4161-9513-ab8d9e74de27" />


### `social_media_events()`

```
from social_media_functions.parse_metadata import social_media_events

t = social_media_events(
    instagram_folder="data/instagram_data",
    tiktok_json="data/tiktok_data/user_data_tiktok.json"
)

t.show(5)
```
Output: Combined table of Instagram and TikTok events in a unified format.

<img width="671" height="391" alt="Screenshot 2026-05-01 at 1 31 51 AM" src="https://github.com/user-attachments/assets/e4cd5fbd-af86-49d5-bf97-d444724c3830" />

## Optional Parameters
All three functions (parse_metadata, tiktok_events, social_media_events) support the following:

### Date Filtering
```
start_date="04-24-2025"
end_date="04-30-2025"
```
Supported Formats Include: 
- "MM-DD-YYYY"
- "YYYY-MM-DD"
- "MM/DD/YYYY"

Example: 
```
t = social_media_events(
    instagram_folder="data/instagram_data",
    tiktok_json="data/tiktok_data/user_data_tiktok.json",
    start_date="04-24-2025",
    end_date="04-30-2025"
)
```

### Timezone (tz)
All functions accept a timezone parameter:
```
tz="America/New_York"  # default
```
Example: 
```
 t = social_media_events(
    instagram_folder="data/instagram_data",
    tiktok_json="data/tiktok_data/user_data_tiktok.json",
    tz="America/Los_Angeles"
)
```
## EventTable Utilities (time_features.py)
### `hide(*cols)`
- Removes specified columns from the table.
```
t.hide("timestamp_unix", "relative_day_index")
```

### `get_time_conversions(features)`
Adds derived time-based columns.
Supported features:
- "hour"
- "weekday"
- "month"
- "year"
- "date"

Wrap Table: 
```
from social_media_functions.parse_metadata.time_features import EventTable
et = EventTable(t)

```
Output: 
<img width="1045" height="234" alt="Screenshot 2026-05-02 at 10 46 32 PM" src="https://github.com/user-attachments/assets/77e7646b-0742-4b9a-a3d4-d2b9d2e15354" />

Add Time-based Features
```
et_time = et.get_time_conversions(["hour", "weekday", "date"])
et_time.table.show(5)
```
Example: 
```
events_by_weekday = et_time.table.group("weekday").sort("weekday")
events_by_weekday.show()
```
Output:
<img width="166" height="192" alt="Screenshot 2026-05-02 at 10 47 18 PM" src="https://github.com/user-attachments/assets/831f8027-5719-4096-80da-34441b927e61" />


## Analysis Functions

### Count Events by Platform
```
from social_media_functions.parse_metadata import social_media_events

t = social_media_events(
    instagram_folder="data/instagram_data",
    tiktok_json="data/tiktok_data/user_data_tiktok.json"
)
t.group("platform")
```
Output: Table showing the number of events grouped by platform (Instagram vs TikTok).

<img width="132" height="70" alt="Screenshot 2026-05-01 at 2 30 16 AM" src="https://github.com/user-attachments/assets/be7660d2-ceb5-4180-a722-66623b62e4ee" />

### Count Events by Object Type (posts, reels, videos, etc.)
```
from social_media_functions.parse_metadata import social_media_events

t = social_media_events(
    instagram_folder="data/instagram_data",
    tiktok_json="data/tiktok_data/user_data_tiktok.json"
)
t.group("object_type")
```
Output: Table showing counts of events by content type (e.g., videos, stories).


<img width="146" height="95" alt="Screenshot 2026-05-01 at 2 32 00 AM" src="https://github.com/user-attachments/assets/c23da723-11ef-4e8d-91b5-23b9d189197d" />

### Select Only Certain Columns
```
from social_media_functions.parse_metadata import social_media_events

t = social_media_events(
    instagram_folder="data/instagram_data",
    tiktok_json="data/tiktok_data/user_data_tiktok.json"
)
t.select("platform", "action_type", "timestamp")

```
Output: Filtered table showing only selected columns for focused analysis.


<img width="347" height="243" alt="Screenshot 2026-05-01 at 2 34 15 AM" src="https://github.com/user-attachments/assets/3dc6faad-58ac-4f87-84f6-b4a4e21d8058" />

### Count by Hour
```
from social_media_functions.parse_metadata import social_media_events

t = social_media_events(
    instagram_folder="data/instagram_data",
    tiktok_json="data/tiktok_data/user_data_tiktok.json"
)
def get_hour(ts):
    return ts.hour

t = t.with_column("hour", t.apply(get_hour, "timestamp_dt"))
t.group("hour")

```
Output: Table showing activity frequency by hour of the day.

<img width="98" height="242" alt="Screenshot 2026-05-01 at 2 35 10 AM" src="https://github.com/user-attachments/assets/2a5ef64b-2214-4410-9ed3-1495fb12def2" />




## Creators

Amreen Adams and Giancarlos Aviles

Questions? Reach out:  
AD70738@umbc.edu  
gaviles1@umbc.edu
















