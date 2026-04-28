# TEEM2
Social Media Parser: A unified Instagram + TikTok data parser for teaching and analysis.

This project loads, cleans, and merges Instagram and TikTok export data into a single, consistent table. It is designed for beginner‑friendly data analysis with clear error messages, flexible date filtering, and simple helper functions.

Features:

- Instagram + TikTok support

- Automatic cleaning + timestamp normalization

- Flexible date filtering

- Friendly, student‑oriented error messages

- Helper functions for hourly, weekday, and daily summaries

- Unified schema across platforms

Quickstart:

import sys

sys.path.append('/content/TEEM2/TEEM2-main')

from social_media_functions.parse_metadata.main_parser import social_media_events

events = social_media_events()

events.show(5)

Filter by date:

social_media_events(start_date="12-01-2025", end_date="1-8-2026")

Required Folder Structure:
<img width="719" height="358" alt="Screenshot 2026-04-28 at 4 26 41 PM" src="https://github.com/user-attachments/assets/ddd4f706-f039-43ec-a657-b49736d52e08" />

Documentation:

- Full Takeout Guide:
How to download, unzip, and organize your Instagram + TikTok data

Can be found here: docs/social_media_takeout_guide.md

- Full Project Documentation
Detailed explanation of functions, schema, and error handling

Can be found here: docs/parser_documentation.md

Error Handling: 

The parser uses a custom exception: StudentInputError

Errors include friendly messages and suggested fixes, such as:

- Missing Instagram folder

- Missing TikTok file

- Wrong date format

- End date before start date

- Empty string paths

Credits:
Developed by Amreen Adams and Giancarlos Aviles




