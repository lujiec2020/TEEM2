Creators: Amreen Adams and Giancarlos Aviles

Questions? Reach out: AD70738@umbc.edu, gaviles1@umbc.edu

Social Media Parser Overview: 

The Social Media Parser requires official data exports from Instagram and TikTok.
This guide walks you through:
- How to download your data
- What files matter
- Where to place them in your project
- How to avoid common student mistakes

Data Extraction: Instagram 

Export your Instagram information from Accounts Center to a device

Instagram Data Takeout Instructions:

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

Inside, you’ll see folders such as:

<img width="717" height="136" alt="Screenshot 2026-04-28 at 4 07 57 PM" src="https://github.com/user-attachments/assets/cc55e9d0-12bb-4768-bc4b-9b244114313f" />


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

<img width="719" height="177" alt="Screenshot 2026-04-28 at 4 06 58 PM" src="https://github.com/user-attachments/assets/83a6614f-61c9-400f-bd6b-536345ccbb40" />


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
<img width="717" height="94" alt="Screenshot 2026-04-28 at 4 06 19 PM" src="https://github.com/user-attachments/assets/7533d8ec-97c6-4316-90fa-3235e1a33dac" />


Required Folder Structure: 
Your project must look like this:

If the folders are missing, create them manually. 

<img width="712" height="404" alt="Screenshot 2026-04-28 at 3 59 06 PM" src="https://github.com/user-attachments/assets/d8733c91-87ce-4159-87bf-78b6384e5a4b" />


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

Common Instagram Errors
<img width="716" height="203" alt="Screenshot 2026-04-28 at 4 04 28 PM" src="https://github.com/user-attachments/assets/ca898000-d703-4bca-ab44-299841825a29" />

Common Tiktok Errors
<img width="721" height="208" alt="Screenshot 2026-04-28 at 4 04 14 PM" src="https://github.com/user-attachments/assets/d9e9e815-8dce-4bcb-8f87-c99b82b49608" />







