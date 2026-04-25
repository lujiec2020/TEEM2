Creators: Amreen Adams and Giancarlos Aviles
Questions? Reach out: AD70738@umbc.edu, gaviles1@umbc.edu

Parser Overview: This library helps students extract and analyze social media data in a
structured and accessible way for projects and learning. The social_media_parser allows users
to upload their own social media data (e.g., TikTok and Instagram) in JSON format and converts
it into structured tables for further analysis and visualization.

Data Extraction:
Instagram: Export your Instagram information from Accounts Center to a device
Instagram Data Takeout Instructions

1.  Click the More icon in the bottom left, then click Settings
2.  Click Accounts Center, then click Your information and permissions.
3.  Click Export your information.
4.  Click Create export.
5.  Select the profile you’d like to export information from.

6.  Click Next.
7.  Select Export to device.
8.  From here, you can choose specific info to export, select a date range, format, the
notification email, and media quality. Make sure to download a JSON file format

9.  Once you have customized your export, click Start export.
10. Data exportation can take anywhere from a few hours to multiple days

TikTok Functions Guide (Student Walkthrough)

1)

tiktok_events(...)

What it does:

Reads your TikTok export JSON and converts it into a datascience Table of
timestamped activity events.

What it outputs (Table columns):

●  platform – always "tiktok"

●  object_type – what the action is about (ex: video, search, comment, share)

●  action_type – the action taken (ex: watch, like, search, comment, share, repost)

●  username – "self" (your own activity)

●

target – link/URL when available (ex: video link)

●  value – text content when available (ex: search term or comment text)

●

timestamp – readable timestamp (already converted to your selected timezone)

●

timestamp_dt – datetime version used internally

●  hour, weekday, date – helpful time columns for grouping and visuals

Example (all time):

None

from src.tiktok_tables.tiktok_events import tiktok_events

t = tiktok_events("data/user_data_tiktok.json",

tz="America/New_York")

t.show(10)

Example (custom date range):

None

t_range = tiktok_events(

    "data/user_data_tiktok.json",

    tz="America/New_York",

    start_date="12-16-2025",

    end_date="1-8-2026"

)

t_range.show(10)

2)

tiktok_watch_summary(t)

What it does:

Creates a simple summary of watch behavior from the TikTok events table.

What it outputs:

A dictionary of small tables you can display with .show():

●

total – total number of watch events

●  by_hour – watch count by hour of day

●  by_weekday – watch count by weekday

●  by_date – watch count by date (daily activity)

Example:

None

from src.tiktok_tables.tiktok_events import tiktok_events,

tiktok_watch_summary

t = tiktok_events("data/user_data_tiktok.json",

tz="America/New_York")

summary = tiktok_watch_summary(t)

summary["total"].show()

summary["by_hour"].show(10)

summary["by_weekday"].show()

summary["by_date"].show(10)

3)

tiktok_late_night_binge(t, ...)

What it does:

Measures how much of your watch activity happens during late-night hours (default:
11 PM–4 AM).

This helps identify a “late-night scrolling” pattern.

Key output metric:

●

late_night_share – the percentage of watch events that happened in the
late-night hours

Parameters you can change:

●  start_hour and end_hour – define the late-night window (wraps past midnight)

●  start_date and end_date – optional date filtering (same format as above)

Example (late-night behavior for a date range):

None

from src.tiktok_tables.tiktok_events import tiktok_events,

tiktok_late_night_binge

t = tiktok_events("data/user_data_tiktok.json",

tz="America/New_York")

binge = tiktok_late_night_binge(

    t,

    start_hour=23,   # 11 PM

    end_hour=4,      # 4 AM

    start_date="12-16-2025",

    end_date="1-8-2026"

)

binge["summary"].show()

binge["late_by_date"].show(10)

How to interpret late_night_share:

If late_night_share = 21.89%, that means 21.89% of your watch events occurred
between 11 PM and 4 AM (within the chosen date range).

4)

tiktok_doomscroll_indicator(t, ...)

What it does:

Produces a “doomscroll indicator” by identifying heavy watch days using:

●  high daily watch volume

●

late-night watch activity

●  estimated session count (based on gaps between watches)

This helps find your most intense usage days.

Parameters you can change:

●  session_gap_minutes – defines when a new “session” starts (default: 20

minutes)

●

late_start and late_end – defines late-night hours (default: 11 PM–4 AM)

●  start_date and end_date – optional date filtering

●

top_n_days – how many top days to show

Outputs:

●  summary – overview of the settings and totals

●  day_scores – the top days ranked by doomscroll_score

Example (doomscroll report for a date range):

None

from src.tiktok_tables.tiktok_events import tiktok_events,

tiktok_doomscroll_indicator

t = tiktok_events("data/user_data_tiktok.json",

tz="America/New_York")

doom = tiktok_doomscroll_indicator(

    t,

    start_date="12-16-2025",

    end_date="1-8-2026",

    session_gap_minutes=20,

    top_n_days=10

)

doom["summary"].show()

doom["day_scores"].show(10)

How to read day_scores:

●  watch_events – total watch events that day

●

late_night_watch_events – how many watches occurred in late-night hours

●  sessions_est – estimated number of sessions that day

●  doomscroll_score – a combined score (higher = heavier usage day)

