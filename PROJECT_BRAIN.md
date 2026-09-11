# PROJECT_BRAIN — telegram-group-member-collector-bot

## Purpose

User-account Telethon scraper for unique usernames appearing in group message traffic.

## Architecture

- Single module `scrape_usernames.py`
- Master store: `output/usernames_master.json`
- Progress: `output/scan_progress.json`
- Batches: `output/exports/batch_XXX.csv`
- Session: `telegram_scraper_session.session`

## Workflow

validate env → connect Telethon → resolve groups → historical scrape with FloodWait handling → optional live handler → save on exit

## Security

- Never commit real `API_ID`/`API_HASH`/`PHONE_NUMBER`
- History once contained personal phone/API examples — keep placeholders only in `.env.example`
- Repo is often private; still sanitize docs

## Gotchas

- `GROUP_TARGETS=all` iterates joined dialogs where `is_group`
- Mentions regex collects @handles from text even without sender username
- Excel locking can block batch CSV writes — warning printed
