<div align="center">
  <img src="https://github.com/user-attachments/assets/b6ce7b92-f871-4ba7-85c8-781c4e38e31d"" alt="" height="200">
</div>

<p align="center">
   
  <a href="https://www.python.org/downloads/">
    <img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/Red-Discordbot">
  </a>
   
  <a href="https://github.com/BarcodeBimbo/Telegram-Channel-Scraper/blob/main/TScan.py">
    <img src="https://img.shields.io/badge/Telegram-python-red.svg" alt="TScan.py">
  </a>
  
</p>


# 📦 Telegram Channel Scraper & Reuploader

An advanced, async Python script to scrape and reupload files from a Telegram channel. Built with automation, progress feedback, deduplication, and efficiency in mind — perfect for mirroring or archiving Telegram content.

---
# Proof Of Concept

<div align="center">
  <video src="https://github.com/user-attachments/assets/15cc3636-b60c-40a0-b5f6-3a7396c1f0ea.mp4"></video>
</div>

---

## 🚀 Features

- ✅ Scrapes all media/files from a source Telegram channel  
- 🔄 Uploads them to your own target channel  
- ⚡ Concurrent uploads with live per-file and total progress bars (via `rich`)  
- 🧠 Smart deduplication using file name, size, and SHA1 hash  
- 🗂️ SQLite DB to track uploads and avoid reprocessing  
- 📥 Realtime download monitoring with size tracking  
- 🧹 Automatically deletes files after successful upload  
- 💡 Simple config system (saved to `config.json`)  

---

## 🔧 Setup

### 1. Install Python 3.11+
Make sure you have Python 3.11 or newer installed.

### 2. Clone the Repo

```bash
git clone https://github.com/BarcodeBimbo/Telegram-Channel-Scraper.git
cd Telegram-Channel-Scraper
```

### 3. Get Telegram API ID & Hash

1. Go to [https://my.telegram.org](https://my.telegram.org)
2. Log in with your phone number and confirmation code
3. Click on **API Development Tools**
4. Fill out:
   - **App title**: any name (e.g., `ChannelScraper`)
   - **Short name**: any short identifier (e.g., `scraper`)
5. Submit the form
6. Copy your **API ID** and **API Hash**

---

### 4. Run the Script

```bash
python3 TScan.py
```

The script will:
- Prompt for your `api_id`, `api_hash`, `source_channel`, and `target_channel`
- Save them to `config.json` for future runs
- Start scraping and uploading automatically

---

## 🖥️ Dependencies

These are auto-installed on first run:

- `telethon`  
- `rich`  
- `aiosqlite`  

To install manually:

```bash
pip install telethon rich aiosqlite
```

---

## ⚙️ Configuration

Stored in `config.json` after first run:

```json
{
  "api_id": 0,
  "api_hash": "api_hash",
  "source_channel": "source_channel",
  "target_channel": "target_channel"
}
```

---

## 📊 Example Output

```
[🔍] Scanning source channel...
[📦] Found 82 files (6.32 GB)

Downloading: big_data.csv ━━━━━━━━ 24.1/120.3 MB • 2.4 MB/s
Uploading: big_data.csv ━━━━━━━━━━ 120.3/120.3 MB • 3.2 MB/s
[📤] Uploaded: big_data.csv

✅ Done. Uploaded 82 files in 312.4s (20.7 MB/s)
```

---

## 📁 File Structure

```
.
├── TScan.py           # Main script
├── config.json        # Generated at first run
├── uploads.db         # SQLite DB to track uploads
├── downloads/         # Folder for downloaded files
└── upload_log.txt     # Upload logs
```

---

## 🛡️ Legal Disclaimer

This tool **only works on Telegram channels you have access to**.  
It is your responsibility to comply with Telegram's [Terms of Service](https://telegram.org/tos) and local laws.

---

## ❤️ Credits

Made by **Sanction Team**  
Telegram: [@SanctionInfoBot](https://t.me/SanctionInfoBot)  
Website: [https://tlo.sh](https://tlo.sh)
