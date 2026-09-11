# Telegram Group Username Scraper

Scrape unique usernames from Telegram **groups** you have joined. Collects usernames from people who post and from `@mentions` in messages. Removes duplicates and saves to CSV/JSON.

Uses your **Telegram user account** (Telethon) — **not** a @BotFather bot token.

---

## Table of Contents

1. [Requirements](#requirements)
2. [Full Setup Guide](#full-setup-guide)
3. [How to Run the Bot](#how-to-run-the-bot)
4. [What You See in Terminal](#what-you-see-in-terminal)
5. [How to Stop and Restart](#how-to-stop-and-restart)
6. [Where to Find Your Data](#where-to-find-your-data)
7. [Configuration (.env)](#configuration-env)
8. [Features](#features)
9. [Important Notes](#important-notes)
10. [Common Questions (FAQ)](#common-questions-faq)
11. [Troubleshooting](#troubleshooting)
12. [Quick Start](#quick-start-copy-paste)
13. [Project Structure](#project-structure)

---

## Requirements

- Windows PC (or any OS with Python)
- **Python 3.10+** installed
- **Telegram account** (your phone number)
- **API_ID** and **API_HASH** from [my.telegram.org/apps](https://my.telegram.org/apps)
- You must **join the groups** you want to scrape with the same Telegram account

---

## Full Setup Guide

### Step 1 — Open project folder in terminal

```powershell
cd "C:\Users\Shamrat\Desktop\Teligram bot"
```

### Step 2 — Install Python packages (first time only)

```powershell
pip install -r requirements.txt
```

### Step 3 — Get API_ID and API_HASH

1. Open [https://my.telegram.org](https://my.telegram.org) in your browser
2. Log in with your phone number
3. Enter the code from your **Telegram app** (chat from "Telegram" — not SMS)
4. Click **API development tools**
5. Create an app:
   - **App title:** `Username Scraper` (any name)
   - **Short name:** `scrapertool` (5–32 letters, no spaces)
   - **Platform:** **Desktop**
   - **Description:** optional
6. Click **Create application**
7. Copy **App api_id** and **App api_hash**

### Step 4 — Create your `.env` file

```powershell
copy .env.example .env
```

Open `.env` in a text editor and paste your real values:

```env
API_ID=38951205
API_HASH=your_32_character_hash_here
PHONE_NUMBER=+8801792911253
GROUP_TARGETS=all
LIVE_MODE=true
LIVE_SCRAPE_HISTORY=true
AUTO_SAVE_INTERVAL=100
BATCH_SIZE=10000
```

> **Important:** Put secrets in `.env` only — **not** in `.env.example`.

### Step 5 — Join Telegram groups

Before running, join the public/private groups you want to scrape using the **same Telegram account** you will use to log in.

---

## How to Run the Bot

### Open terminal in project folder

```powershell
cd "C:\Users\Shamrat\Desktop\Teligram bot"
```

### Run command (recommended)

```powershell
python scrape_usernames.py --live
```

This is the **best mode** for daily use:
1. Scans **all old messages** in your groups (history)
2. Then **watches for new messages** (live)
3. **Auto-saves** progress — safe to stop anytime

---

### All run commands

| Command | What it does |
|---------|--------------|
| `python scrape_usernames.py --live` | **Recommended** — history scan + live monitoring |
| `python scrape_usernames.py` | One-time scrape only (no live watch) |
| `python scrape_usernames.py --live --no-history` | Live only — skip old messages, watch new ones only |

---

### First run — phone login

Add your phone to `.env` (first login only):

```env
PHONE_NUMBER=+8801792911253
```

On **first run**, terminal only asks for the **OTP code**:

```
Logging in with phone from .env: +8801792911253
Please enter the code you received: 12345
```

| Step | What to do |
|------|------------|
| Phone | Set in `.env` — international format, **no spaces** |
| OTP code | Check **Telegram app** → chat from **Telegram** (official) |

> **Do not put OTP in `.env`** — it expires in minutes. Only phone number goes there.

After login, a session file is saved (`telegram_scraper_session.session`). Next runs **won't ask phone or OTP again**.

---

### Only run ONE bot at a time

**Never run two terminals** with the bot at the same time.

If you see `database is locked` error:
1. Press **Ctrl+C** in all terminals running the bot
2. Close any duplicate Python processes in Task Manager
3. Run **only one** instance again

---

## What You See in Terminal

### Normal startup

```
Loaded 335 existing username(s) from output\usernames_master.json

Connecting to Telegram...
Logged in as: Md (@shamrat52)

Finding all groups you have joined...
Found 28 joined group(s).

Live mode: scanning history (resume + auto-save), then watching new messages...

[1/28] Scanning: OKX English
  Reading messages (duplicates skipped, auto-save enabled)...
  ... OKX English: 500 messages, 400 unique usernames total
  [saved] 1000 usernames -> usernames_master.json + 4 batch file(s) in exports/
```

### When a group is already done

```
[2/28] Skipping: Some Group (done)
```

### When resuming after restart

```
Resuming: OKX English from message offset 288000
```

### Live mode (after history scan)

```
LIVE MODE — watching for new messages
  Monitoring 28 group(s)
  Press Ctrl+C to stop

+ NEW @someuser  from: OKX English  [total: 1200]
```

---

## How to Stop and Restart

### Stop the bot

Press **Ctrl+C** in the terminal.

You will see:

```
Progress and usernames saved on exit.
```

Your data is saved to:
- `output/usernames_master.json`
- `output/exports/batch_*.csv`
- `output/scan_progress.json`

### Restart the bot

```powershell
cd "C:\Users\Shamrat\Desktop\Teligram bot"
python scrape_usernames.py --live
```

On restart:
- **Usernames** — loaded from file, no duplicates added
- **Finished groups** — skipped automatically
- **Unfinished groups** — resume from last message

### Fast restart (skip history, live only)

After your first full scan is done, use this for faster restarts:

```powershell
python scrape_usernames.py --live --no-history
```

Or set in `.env`:

```env
LIVE_SCRAPE_HISTORY=false
```

---

## Where to Find Your Data

### Folder location

```
C:\Users\Shamrat\Desktop\Teligram bot\output\
```

### Open output folder

```powershell
explorer "C:\Users\Shamrat\Desktop\Teligram bot\output"
```

### Open batch files in Excel

```powershell
explorer "C:\Users\Shamrat\Desktop\Teligram bot\output\exports"
```

```powershell
start excel "C:\Users\Shamrat\Desktop\Teligram bot\output\exports\batch_001.csv"
```

### Output files

| File | Description |
|------|-------------|
| `output/exports/batch_001.csv` | **Open in Excel** — up to 10,000 users per file |
| `output/exports/batch_002.csv` | Next 10,000 users, and so on |
| `output/usernames_master.json` | Bot memory (no duplicates) — do not delete |
| `output/scan_progress.json` | Resume position per group |
| `output/usernames_YYYYMMDD_*.csv` | Snapshot (one-time scrape mode only) |

### CSV columns

| Column | Meaning |
|--------|---------|
| `username` | Telegram @username |
| `user_id` | Numeric Telegram user ID (empty if unknown) |
| `groups` | Group names where this user was found |

---

## Configuration (.env)

| Variable | Example | Description |
|----------|---------|-------------|
| `API_ID` | `38951205` | From [my.telegram.org/apps](https://my.telegram.org/apps) |
| `API_HASH` | `abc123...` | 32-character hash from same page |
| `PHONE_NUMBER` | `+8801792911253` | Your phone for first login (no spaces) |
| `GROUP_TARGETS` | `all` | `all` = every joined group, or `group1,group2` |
| `LIVE_MODE` | `true` | Keep running and watch new messages |
| `LIVE_SCRAPE_HISTORY` | `true` | Scan old messages before live mode |
| `AUTO_SAVE_INTERVAL` | `100` | Save JSON + batches after every N new usernames |
| `BATCH_SIZE` | `10000` | Users per batch file in `output/exports/` |

### GROUP_TARGETS examples

```env
# All groups you joined
GROUP_TARGETS=all

# Specific groups only
GROUP_TARGETS=okxenglish,cryptogroup,https://t.me/somegroup
```

---

## Features

- **Multi-group** — scan all joined groups with `GROUP_TARGETS=all`
- **No duplicates** — same username saved once across all groups
- **Auto-save** — every 100 usernames + progress every 500 messages
- **Save on stop** — Ctrl+C saves everything
- **Resume** — continues from last message per group
- **Skip done groups** — completed groups not rescanned on restart
- **Live mode** — captures new usernames as messages arrive
- **Speed cache** — fewer API calls for faster scanning

---

## Important Notes

1. **Join groups first** — your account must be a member to read messages.
2. **Not a bot token** — do not use @BotFather token. Use `API_ID` + `API_HASH` only.
3. **Channels not scanned** — standalone channels like `@catiqofficial` are not included. Only **groups**.
4. **Hidden member lists** — still works; usernames come from messages, not member list.
5. **Large groups** — full history can take hours or days. Stop anytime — progress is saved.
6. **Only users with @username** are collected — not everyone has one.
7. **One instance only** — running two bots at once causes `database is locked` error.
8. **Open batch files in Excel** — not the JSON file. Each batch has up to 10,000 rows (fast).

---

## Common Questions (FAQ)

### Output files — what does each do?

| File | Purpose | Can I delete? |
|------|---------|---------------|
| `output/usernames_master.json` | **Bot memory** — all usernames, no duplicates | **No** |
| `output/exports/batch_*.csv` | **Excel files** — 10,000 users each | Yes (bot recreates on save) |
| `output/scan_progress.json` | **Scan position** (where bot stopped) | **No** |

**Simple rule:** Bot memory = **JSON + progress**. Open **batch files** in Excel.

---

### Batch files (for Excel)

Every **10,000 users**, bot creates/updates files in `output/exports/`:

```
batch_001.csv  →  users 1–10,000
batch_002.csv  →  users 10,001–20,000
batch_003.csv  →  users 20,001–30,000
...
```

Last batch may have fewer than 10,000 until it fills up.

**On restart:** bot reads JSON and rebuilds all batch files automatically (including existing 40k+ data).

---

### I copied batch data to my Excel — can I delete batch files?

**Yes** — bot recreates them from JSON on next save.

**Do NOT delete** `usernames_master.json` or `scan_progress.json`.

---

### If I delete everything in `output/` folder?

| Result |
|--------|
| All usernames **gone** |
| Scan starts **from beginning** |
| Fresh start like day one |

---

### Move bot to another computer?

Copy the whole folder. **Must include:**

| File | Why |
|------|-----|
| `output/usernames_master.json` | Old usernames |
| `output/scan_progress.json` | Resume position |
| `output/exports/` | Batch Excel files (optional) |
| `.env` | API keys + phone |
| `telegram_scraper_session.session` | Login (may skip OTP) |

On new PC: `pip install -r requirements.txt` then `python scrape_usernames.py --live`

Use the **same Telegram account**.

---

### Upload to GitHub — is my data safe?

**Yes.** `.gitignore` blocks private files:

| Not uploaded to GitHub | Uploaded (safe) |
|------------------------|-----------------|
| `.env` (your keys) | `scrape_usernames.py` |
| `output/` (your usernames) | `README.md` |
| `*.session` (your login) | `.env.example` (template only) |

**People who `git clone` get a fresh bot** — they use their own account, API keys, and start with zero data.

---

### What goes in `.env`?

| Put in `.env` | Do NOT put in `.env` |
|---------------|----------------------|
| `API_ID` | OTP code (expires in minutes) |
| `API_HASH` | @BotFather bot token |
| `PHONE_NUMBER` | Scraped usernames |
| `GROUP_TARGETS` | |

OTP is entered **once in terminal** on first login only.

---

### What groups and messages does the bot check?

| Checks | Does NOT check |
|--------|----------------|
| Groups you **joined** (`GROUP_TARGETS=all`) | Channels (e.g. `@catiqofficial`) |
| All old messages (history) | Groups you **left** |
| New messages (live mode) | Hidden member lists |
| Post authors with `@username` | Users without `@username` |
| `@mentions` in message text | |

---

### Does bot store data inside the `.py` file?

**No.** Data lives only in `output/` folder while running (temporary RAM for speed). Permanent storage = **CSV + JSON** in `output/`.

---

### Will bot get slow with 1 lakh (100,000) usernames?

| Part | Slow? |
|------|-------|
| Message scanning | **No** — Telegram limits matter more |
| Saving CSV/JSON | **Slightly** — bigger files take longer to save |
| RAM usage | **Fine** — ~10–20 MB for 100k users |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Missing API_ID / API_HASH` | Fill real values in `.env` (not `.env.example`) |
| `PhoneNumberInvalidError` | Use `+8801792911253` format — no spaces, correct digits |
| No login code | Check Telegram app → chat from **Telegram** (not SMS) |
| `database is locked` | Stop all running bots. Run only **one** instance |
| No CSV file yet | Wait for `[checkpoint]` or `[saved]` in terminal |
| Bot slow after many messages | Normal — Telegram rate limits. Bot auto-waits and continues |
| Red marks in `.env` file | IDE false alarm — file works fine. Use `.env` not `.env.example` |
| Data lost after stop (old version) | Update to latest script — now saves on stop and every 500/1000 |
| Terminal count ≠ batch files | Restart bot — batches rebuild from JSON |

---

## Quick Start (copy-paste)

```powershell
cd "C:\Users\Shamrat\Desktop\Teligram bot"
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` with your API_ID and API_HASH, then:

```powershell
python scrape_usernames.py --live
```

View batch results:

```powershell
explorer "C:\Users\Shamrat\Desktop\Teligram bot\output\exports"
```

---

## Project Structure

```
Teligram bot/
├── scrape_usernames.py              # Main bot script
├── requirements.txt                 # Python dependencies
├── .env                             # Your secrets (do not share)
├── .env.example                     # Template for .env
├── telegram_scraper_session.session # Login session (auto-created)
├── output/
│   ├── usernames_master.json        # Bot memory (all usernames)
│   ├── scan_progress.json           # Resume data
│   └── exports/
│       ├── batch_001.csv            # Excel — 10,000 users each
│       ├── batch_002.csv
│       └── ...
└── README.md                        # This file
```
#   t e l e g r a m - g r o u p - m e m b e r - c o l l e c t o r - b o t  
 