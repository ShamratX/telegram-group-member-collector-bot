# Telegram Group Member Collector Bot

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Telethon](https://img.shields.io/badge/Telethon-user%20API-2CA5E0)](https://docs.telethon.dev/)

Collect unique Telegram **@usernames** from **groups** you have joined. Reads message authors and `@mentions`, dedupes across groups, and saves JSON/CSV.

Uses your **Telegram user account** (Telethon) — **not** a BotFather bot token.

## Features

- Multi-group scrape (`GROUP_TARGETS=all` or an explicit list)
- One-time history scrape and/or live monitor (`--live`)
- Auto-save + resume after Ctrl+C
- Batch CSV exports for Excel (`output/exports/`)

## How it works

Telethon logs in as your user, resolves target groups, iterates historical messages (with progress offsets), extracts usernames, then optionally watches `NewMessage` events to append newcomers.

## Requirements

- Python 3.10+
- Telegram account
- `API_ID` + `API_HASH` from [my.telegram.org/apps](https://my.telegram.org/apps)
- Membership in target groups

## Quick start

```bash
git clone https://github.com/ShamratX/telegram-group-member-collector-bot.git
cd telegram-group-member-collector-bot
python -m pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your API credentials and phone (international format). Never commit `.env`.

```bash
python scrape_usernames.py --live
```

First run asks for the OTP from the official Telegram chat. Session file is saved for later runs.

## Usage

| Command | Purpose |
|---------|---------|
| `python scrape_usernames.py --live` | History + live (recommended) |
| `python scrape_usernames.py` | History only |
| `python scrape_usernames.py --live --no-history` | Live only |

Run **one** instance only (`database is locked` if two).

## Config (`.env` names)

`API_ID`, `API_HASH`, `PHONE_NUMBER`, `GROUP_TARGETS`, `LIVE_MODE`, `LIVE_SCRAPE_HISTORY`, `AUTO_SAVE_INTERVAL`, `BATCH_SIZE`

## Project structure

```text
scrape_usernames.py
requirements.txt
.env.example
output/   # gitignored results
```

## Limitations

- Channels are not scraped — groups only.
- Users without a public `@username` are skipped.
- Large histories can take a long time; resume is supported.
- Keep phone / API secrets out of README and `.env.example`.

## License

Private project.
