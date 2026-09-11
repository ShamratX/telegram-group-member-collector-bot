# Telegram Group Member Collector Bot

Collect unique Telegram **@usernames** from groups you have joined. Reads message authors and `@mentions`, removes duplicates, and saves CSV/JSON.

Uses your **Telegram user account** via [Telethon](https://docs.telethon.dev/) — **not** a BotFather bot token.

## Features

- Multi-group scrape (`GROUP_TARGETS=all` or a list)
- Deduped usernames across groups
- One-time scrape or live monitor (`--live`)
- Auto-save + resume after Ctrl+C
- Batch CSV exports for Excel

## Requirements

- Python 3.10+
- Telegram account
- `API_ID` + `API_HASH` from [my.telegram.org/apps](https://my.telegram.org/apps)
- Join target groups with the **same** account before scraping

## Quick start

```bash
git clone https://github.com/ShamratX/telegram-group-member-collector-bot.git
cd telegram-group-member-collector-bot
python -m pip install -r requirements.txt
cp .env.example .env
```

On Windows PowerShell use `copy .env.example .env`.

Edit `.env` with your real values (never commit `.env`):

```env
API_ID=your_api_id
API_HASH=your_api_hash
PHONE_NUMBER=+1234567890
GROUP_TARGETS=all
LIVE_MODE=true
LIVE_SCRAPE_HISTORY=true
```

Then run:

```bash
python scrape_usernames.py --live
```

First login asks for the OTP from the official **Telegram** chat in the app. A session file is saved so later runs skip phone/OTP.

## Usage

| Command | What it does |
|---------|----------------|
| `python scrape_usernames.py --live` | History scan + live watch (recommended) |
| `python scrape_usernames.py` | One-time history scrape only |
| `python scrape_usernames.py --live --no-history` | Live only (skip old messages) |

Stop anytime with **Ctrl+C** — progress and usernames are saved. Run the same command again to resume.

Run **only one** instance at a time. Two terminals cause `database is locked`.

## Config (`.env`)

| Variable | Description |
|----------|-------------|
| `API_ID` | From [my.telegram.org/apps](https://my.telegram.org/apps) |
| `API_HASH` | Same page (keep secret) |
| `PHONE_NUMBER` | International format, no spaces — first login only |
| `GROUP_TARGETS` | `all` / `*` = every joined group, or `group1,group2` |
| `LIVE_MODE` | `true` to watch new messages without `--live` |
| `LIVE_SCRAPE_HISTORY` | `true` = scan history before live |
| `AUTO_SAVE_INTERVAL` | Save after every N new usernames (default `100`) |
| `BATCH_SIZE` | Users per `output/exports/batch_*.csv` (default `10000`) |

### Get API_ID / API_HASH

1. Open https://my.telegram.org → log in with your phone
2. Enter the code from Telegram app
3. **API development tools** → create an app (Desktop)
4. Copy **api_id** and **api_hash** into `.env`

### GROUP_TARGETS examples

```env
GROUP_TARGETS=all
GROUP_TARGETS=okxenglish,cryptogroup,https://t.me/somegroup
```

## Project structure

```text
telegram-group-member-collector-bot/
├── scrape_usernames.py       # Main script
├── requirements.txt
├── .env.example              # Template (safe to commit)
├── .env                      # Your secrets (gitignored)
├── telegram_scraper_session.session   # Login session (gitignored)
└── output/                   # Results (gitignored)
    ├── usernames_master.json
    ├── scan_progress.json
    └── exports/
        └── batch_001.csv
```

## Output

| File | Purpose |
|------|---------|
| `output/usernames_master.json` | Master list (do not delete) |
| `output/scan_progress.json` | Resume positions per group |
| `output/exports/batch_*.csv` | Excel-friendly batches |
| `output/usernames_YYYYMMDD_*.csv` | Snapshot (one-time mode) |

CSV columns: `username`, `user_id`, `groups`.

## Notes

- Put secrets only in `.env` — never in README or `.env.example`.
- Channels are not scraped; **groups** only.
- Users without a public `@username` are skipped.
- Large groups can take a long time; resume is safe.
- Moving PCs: copy `.env`, session file, and `output/` if you want to keep progress.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Missing `API_ID` / `API_HASH` | Fill `.env` (not `.env.example`) |
| `PhoneNumberInvalidError` | Use `+` country code, no spaces |
| No OTP | Check Telegram app → chat from **Telegram** |
| `database is locked` | Close other bot terminals / Python processes |
| Empty exports | Wait for `[saved]` lines, or finish at least one auto-save |

## License

Private project. Keep `.env` and session files off public remotes.
