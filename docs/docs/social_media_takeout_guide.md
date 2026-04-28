Creators: Amreen Adams and Giancarlos Aviles
Questions? Reach out: AD70738@umbc.edu, gaviles1@umbc.edu

Parser Overview: The Social Media Parser requires official data exports from Instagram and TikTok.
This guide walks you through:
- How to download your data
- What files matter
- Where to place them in your project
- How to avoid common student mistakes

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

What Files You Will Receive:
Your ZIP will look like: instagram-<username>-data.zip
Inside, you’ll see folders such as:
comments/
likes/
stories/
messages/
media/

The parser uses only the JSON files, especially:
- story_activities_story_likes.json
- story_activities_polls.json
- comments_reels_comments.json
- post_comments.json

How to Extract and Organize the Files:
1. Unzip the file
2. Locate the folder containing all the JSON files
3. Move all selected JSON files into: data/instagram_data/
4. Your Folder should look like this:
data/
   instagram_data/
       story_activities_story_likes.json
       story_activities_polls.json
       comments_reels_comments.json
       post_comments.json
       ...

Data Extraction:
TikTok: Download your TikTok data to a device (JSON)
TikTok Data Takeout Instructions

1.  Open the TikTok app and go to your Profile.
2.  Tap the ☰ (menu) in the top right, then tap Settings and privacy.
3.  Go to Account (or Privacy) and find Download your data (sometimes listed as Download TikTok data).
4.  Tap Request data / Request download. If TikTok asks for a file format, choose JSON (not HTML / TXT), so it works with this parser.
5.  Wait until the request finishes processing (this can take some time depending on account size).
6.  Return to Download your data and open the Download data tab, then download the export to your device.

What Files You Will Receive:
Your ZIP will contain: user_data_tiktok.json
This is the only file the parser needs.
It includes: Watch history, Likes, Searches, Comments, Shares, Reposts

How to Extract and Organize the Files:
1. Unzip the TikTok export
2. Locate user_data_tiktok.json
3. Move it into: data/tiktok_data/user_data_tiktok.json
4. Your folder should look like:
 data/
   tiktok_data/
       user_data_tiktok.json

Required Folder Structure:
Your project must look like this:
TEEM2-main/
│
├── data/
│   ├── instagram_data/
│   │     *.json files from Instagram
│   │
│   └── tiktok_data/
│         user_data_tiktok.json
│
├── social_media_functions/
│   └── parse_metadata/
│         main_parser.py
│         utils.py
│         time_features.py
│
└── analysis.ipynb
* If the folders are missing, create them manually.

Troubleshooting: 

Problem: “Instagram folder not found”
Check if Folder name is wrong, Folder is empty, Files are still zipped

Problem: “TikTok file not found”
Check if File is not named user_data_tiktok.json, File is inside a subfolder, File is missing

Problem: “Invalid date format”
Use one of these formats:
MM-DD-YYYY
YYYY-MM-DD
MM/DD/YYYY

Problem: “No data found”
Check if Both Instagram and TikTok paths are wrong, Folders are empty, JSON files missing






