"""
Telegram public group username scraper.

Reads all messages from one or many groups and collects unique usernames
(no duplicates across groups) from message authors and @mentions.

Modes:
  - One-time scrape:  python scrape_usernames.py
  - Live monitoring:  python scrape_usernames.py --live

Setup:
  1. pip install -r requirements.txt
  2. Copy .env.example to .env and fill in API_ID, API_HASH, GROUP_TARGETS
  3. python scrape_usernames.py --live

Get API_ID and API_HASH: https://my.telegram.org/apps
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import re
import signal
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from telethon import TelegramClient, events, utils
from telethon.errors import (
    ChannelInvalidError,
    ChannelPrivateError,
    FloodWaitError,
    UsernameInvalidError,
    UsernameNotOccupiedError,
)
from telethon.tl.types import User

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
GROUP_TARGETS_RAW = os.getenv("GROUP_TARGETS", os.getenv("GROUP_TARGET", "")).strip()
LIVE_MODE = os.getenv("LIVE_MODE", "").strip().lower() in {"1", "true", "yes", "on"}
LIVE_SCRAPE_HISTORY = os.getenv("LIVE_SCRAPE_HISTORY", "true").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}
AUTO_SAVE_INTERVAL = max(1, int(os.getenv("AUTO_SAVE_INTERVAL", "100")))
BATCH_SIZE = max(1, int(os.getenv("BATCH_SIZE", "10000")))
PHONE_NUMBER = os.getenv("PHONE_NUMBER", "").strip()

SESSION_NAME = "telegram_scraper_session"
OUTPUT_DIR = Path("output")
MASTER_JSON = OUTPUT_DIR / "usernames_master.json"
EXPORTS_DIR = OUTPUT_DIR / "exports"
PROGRESS_JSON = OUTPUT_DIR / "scan_progress.json"
MENTION_PATTERN = re.compile(r"@([a-zA-Z][a-zA-Z0-9_]{4,31})")


OUTPUT_FIELDS = ["username", "user_id", "groups"]


@dataclass
class ScrapedUser:
    username: str
    user_id: int | None = None
    groups: list[str] = field(default_factory=list)


@dataclass
class GroupProgress:
    title: str
    offset_id: int = 0
    completed: bool = False
    messages_scanned: int = 0


def validate_config() -> None:
    missing = []
    if not API_ID or API_ID == "12345678":
        missing.append("API_ID")
    if not API_HASH or API_HASH == "your_api_hash_here":
        missing.append("API_HASH")
    if not GROUP_TARGETS_RAW:
        missing.append("GROUP_TARGETS")

    if missing:
        print("Missing configuration in .env file:")
        for key in missing:
            print(f"  - {key}")
        print("\nCopy .env.example to .env and fill in your values.")
        raise SystemExit(1)


def parse_group_targets(raw: str) -> list[str]:
    parts = re.split(r"[,;\n]+", raw)
    return [part.strip() for part in parts if part.strip()]


def scrape_all_requested(raw: str) -> bool:
    targets = {part.strip().lower() for part in parse_group_targets(raw)}
    return "all" in targets or "*" in targets


def normalize_username(value: str | None) -> str | None:
    if not value:
        return None
    username = value.strip().lstrip("@")
    if not username or username.lower() in {"none", "null"}:
        return None
    return username


def extract_mentions(text: str) -> set[str]:
    if not text:
        return set()
    return {m.lower() for m in MENTION_PATTERN.findall(text)}


def user_to_row(user: ScrapedUser) -> dict:
    return {
        "username": user.username,
        "user_id": user.user_id,
        "groups": ", ".join(user.groups),
    }


def load_master_users() -> dict[str, ScrapedUser]:
    if not MASTER_JSON.exists():
        return rebuild_master_from_batches()

    try:
        with MASTER_JSON.open(encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print(f"WARNING: {MASTER_JSON.name} is corrupted. Rebuilding from batch files...")
        return rebuild_master_from_batches()

    users: dict[str, ScrapedUser] = {}
    for item in data:
        groups = item.get("groups", "")
        if isinstance(groups, str):
            groups = [g.strip() for g in groups.split(",") if g.strip()]
        username = item["username"]
        users[username.lower()] = ScrapedUser(
            username=username,
            user_id=item.get("user_id"),
            groups=groups,
        )
    return users


def load_progress() -> dict[str, GroupProgress]:
    if not PROGRESS_JSON.exists():
        return {}

    with PROGRESS_JSON.open(encoding="utf-8") as f:
        data = json.load(f)

    progress: dict[str, GroupProgress] = {}
    for key, item in data.get("groups", {}).items():
        progress[key] = GroupProgress(
            title=item.get("title", key),
            offset_id=int(item.get("offset_id", 0)),
            completed=bool(item.get("completed", False)),
            messages_scanned=int(item.get("messages_scanned", 0)),
        )
    return progress


def save_progress(progress: dict[str, GroupProgress]) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    payload = {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "groups": {
            key: {
                "title": item.title,
                "offset_id": item.offset_id,
                "completed": item.completed,
                "messages_scanned": item.messages_scanned,
            }
            for key, item in progress.items()
        },
    }
    with PROGRESS_JSON.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return PROGRESS_JSON


def write_batch_file(batch_num: int, users: list[ScrapedUser]) -> Path | None:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = EXPORTS_DIR / f"batch_{batch_num:03d}.csv"
    rows = [user_to_row(user) for user in users]
    try:
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
    except PermissionError:
        print(
            f"\nWARNING: Could not update {path.name} — close it in Excel, then save again.\n"
        )
        return None
    return path


def prune_extra_batch_files(keep_count: int) -> None:
    if not EXPORTS_DIR.exists():
        return
    for path in EXPORTS_DIR.glob("batch_*.csv"):
        try:
            batch_num = int(path.stem.split("_", 1)[1])
        except (IndexError, ValueError):
            continue
        if batch_num > keep_count:
            try:
                path.unlink()
            except OSError:
                print(f"WARNING: Could not remove leftover {path.name}. Close it in Excel if it is open.")


def sync_batch_exports(users_by_key: dict[str, ScrapedUser], *, full: bool = True) -> int:
    users = sorted(users_by_key.values(), key=lambda u: u.username.lower())
    total = len(users)
    if total == 0:
        prune_extra_batch_files(0)
        return 0

    num_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
    batch_numbers = range(1, num_batches + 1) if full else [num_batches]

    for batch_num in batch_numbers:
        start = (batch_num - 1) * BATCH_SIZE
        end = min(batch_num * BATCH_SIZE, total)
        write_batch_file(batch_num, users[start:end])
    prune_extra_batch_files(num_batches)
    return num_batches


def save_master_json(users_by_key: dict[str, ScrapedUser]) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    users = sorted(users_by_key.values(), key=lambda u: u.username.lower())
    rows = [user_to_row(user) for user in users]
    temp_path = MASTER_JSON.with_suffix(".json.tmp")

    with temp_path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
    temp_path.replace(MASTER_JSON)


def rebuild_master_from_batches() -> dict[str, ScrapedUser]:
    if not EXPORTS_DIR.exists():
        return {}

    users: dict[str, ScrapedUser] = {}
    batch_files = sorted(EXPORTS_DIR.glob("batch_*.csv"))
    if not batch_files:
        return users

    print(f"Recovering usernames from {len(batch_files)} batch file(s)...")
    for batch_path in batch_files:
        with batch_path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                username = row.get("username", "").strip()
                if not username:
                    continue
                groups_raw = row.get("groups", "")
                groups = [g.strip() for g in groups_raw.split(",") if g.strip()]
                user_id_raw = row.get("user_id", "").strip()
                user_id = int(user_id_raw) if user_id_raw.isdigit() else None
                key = username.lower()
                if key in users:
                    for group in groups:
                        if group not in users[key].groups:
                            users[key].groups.append(group)
                    if user_id and not users[key].user_id:
                        users[key].user_id = user_id
                    continue
                users[key] = ScrapedUser(username=username, user_id=user_id, groups=groups)

    save_master_json(users)
    print(f"Recovered {len(users)} username(s) into {MASTER_JSON.name}")
    return users


def save_master_users(
    users_by_key: dict[str, ScrapedUser],
    *,
    full_batches: bool = True,
) -> Path:
    save_master_json(users_by_key)
    sync_batch_exports(users_by_key, full=full_batches)
    return MASTER_JSON


def save_snapshot(users_by_key: dict[str, ScrapedUser]) -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    users = sorted(users_by_key.values(), key=lambda u: u.username.lower())
    rows = [user_to_row(user) for user in users]

    json_path = OUTPUT_DIR / f"usernames_{timestamp}.json"
    csv_path = OUTPUT_DIR / f"usernames_{timestamp}.csv"

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    return json_path, csv_path


def add_user(
    users_by_key: dict[str, ScrapedUser],
    username: str,
    group_title: str,
    *,
    user_id: int | None = None,
) -> bool:
    """Add user if new. Returns True when a new unique username was added."""
    key = username.lower()
    if key in users_by_key:
        existing = users_by_key[key]
        if group_title not in existing.groups:
            existing.groups.append(group_title)
        if user_id and not existing.user_id:
            existing.user_id = user_id
        return False

    users_by_key[key] = ScrapedUser(
        username=username,
        user_id=user_id,
        groups=[group_title],
    )
    return True


class SaveTracker:
    def __init__(self, users_by_key: dict[str, ScrapedUser], progress: dict[str, GroupProgress]):
        self.users_by_key = users_by_key
        self.progress = progress
        self.last_saved_user_count = len(users_by_key)

    def save_progress_only(self) -> None:
        save_progress(self.progress)

    def maybe_save_usernames(self, *, force: bool = False) -> None:
        new_users = len(self.users_by_key) - self.last_saved_user_count
        if not force and new_users < AUTO_SAVE_INTERVAL:
            return
        save_master_users(self.users_by_key, full_batches=force)
        save_progress(self.progress)
        self.last_saved_user_count = len(self.users_by_key)
        if new_users > 0 or force:
            batch_count = (len(self.users_by_key) + BATCH_SIZE - 1) // BATCH_SIZE
            print(
                f"  [saved] {len(self.users_by_key)} usernames -> "
                f"{MASTER_JSON.name} + {batch_count} batch file(s) in {EXPORTS_DIR.name}/"
            )

    def save_on_exit(self) -> None:
        save_progress(self.progress)
        if len(self.users_by_key) != self.last_saved_user_count:
            save_master_users(self.users_by_key, full_batches=True)
            batch_count = (len(self.users_by_key) + BATCH_SIZE - 1) // BATCH_SIZE
            print(
                f"  [saved] {len(self.users_by_key)} usernames -> "
                f"{MASTER_JSON.name} + {batch_count} batch file(s) in {EXPORTS_DIR.name}/"
            )
        print("Progress saved on exit.")


async def get_cached_sender(message, sender_cache: dict[int, User]) -> User | None:
    if message.sender and isinstance(message.sender, User):
        return message.sender
    if not message.from_id:
        return None

    sender_id = utils.get_peer_id(message.from_id)
    if sender_id in sender_cache:
        return sender_cache[sender_id]

    sender = await message.get_sender()
    if isinstance(sender, User):
        sender_cache[sender_id] = sender
    return sender if isinstance(sender, User) else None


async def process_message(
    message,
    group_title: str,
    users_by_key: dict[str, ScrapedUser],
    sender_cache: dict[int, User],
) -> list[ScrapedUser]:
    """Extract usernames from one message. Returns list of newly added users."""
    new_users: list[ScrapedUser] = []

    sender = await get_cached_sender(message, sender_cache)
    if sender:
        username = normalize_username(sender.username)
        if username and add_user(
            users_by_key,
            username,
            group_title,
            user_id=sender.id,
        ):
            new_users.append(users_by_key[username.lower()])

    for mention in extract_mentions(message.text or ""):
        if add_user(users_by_key, mention, group_title):
            new_users.append(users_by_key[mention.lower()])

    return new_users


async def resolve_target_groups(client: TelegramClient) -> list[tuple[str, object]]:
    """Return list of (display_title, entity) for each group to scrape."""
    groups: list[tuple[str, object]] = []
    seen_ids: set[int] = set()

    def add_group(title: str, entity: object) -> None:
        entity_id = getattr(entity, "id", None)
        if entity_id is not None and entity_id in seen_ids:
            return
        if entity_id is not None:
            seen_ids.add(entity_id)
        groups.append((title, entity))

    if scrape_all_requested(GROUP_TARGETS_RAW):
        print("Finding all groups you have joined...")
        async for dialog in client.iter_dialogs():
            if not dialog.is_group:
                continue
            title = dialog.name or str(dialog.id)
            add_group(title, dialog.entity)
        print(f"Found {len(groups)} joined group(s).\n")
        return groups

    targets = parse_group_targets(GROUP_TARGETS_RAW)
    explicit_targets = [t for t in targets if t.lower() not in {"all", "*"}]

    for target in explicit_targets:
        try:
            entity = await client.get_entity(target)
        except (UsernameInvalidError, UsernameNotOccupiedError):
            print(f"Warning: Skipping '{target}' — group not found or invalid username.")
            continue
        except (ChannelPrivateError, ChannelInvalidError):
            print(
                f"Warning: Skipping '{target}' — no access. "
                "Join the group with your account first."
            )
            continue

        title = getattr(entity, "title", target)
        add_group(title, entity)

    return groups


def build_group_title_map(target_groups: list[tuple[str, object]]) -> dict[int, str]:
    title_map: dict[int, str] = {}
    for title, entity in target_groups:
        title_map[utils.get_peer_id(entity)] = title
    return title_map


def group_progress_key(entity: object) -> str:
    return str(utils.get_peer_id(entity))


async def scrape_single_group(
    client: TelegramClient,
    group_title: str,
    entity: object,
    users_by_key: dict[str, ScrapedUser],
    progress: dict[str, GroupProgress],
    save_tracker: SaveTracker,
) -> int:
    key = group_progress_key(entity)
    group_state = progress.get(key)
    if group_state and group_state.completed:
        print(f"Skipping: {group_title} (already completed)")
        return group_state.messages_scanned

    if not group_state:
        group_state = GroupProgress(title=group_title)
        progress[key] = group_state

    offset_id = group_state.offset_id
    message_count = group_state.messages_scanned
    sender_cache: dict[int, User] = {}

    if offset_id:
        print(f"Resuming: {group_title} from message offset {offset_id}")
    else:
        print(f"Scanning: {group_title}")

    print("  Reading messages (duplicates skipped, auto-save enabled)...")

    while True:
        try:
            async for message in client.iter_messages(entity, limit=None, offset_id=offset_id):
                message_count += 1
                offset_id = message.id
                group_state.offset_id = offset_id
                group_state.messages_scanned = message_count

                await process_message(message, group_title, users_by_key, sender_cache)
                save_tracker.maybe_save_usernames()

                if message_count % 500 == 0:
                    print(
                        f"  ... {group_title}: {message_count} messages, "
                        f"{len(users_by_key)} unique usernames total"
                    )
                    save_tracker.save_progress_only()

            group_state.completed = True
            save_tracker.maybe_save_usernames(force=True)
            break
        except FloodWaitError as exc:
            print(f"  Rate limit — waiting {exc.seconds}s, then continuing...")
            save_tracker.save_progress_only()
            save_tracker.maybe_save_usernames(force=True)
            await asyncio.sleep(exc.seconds + 1)

    print(f"  Done with {group_title}: {message_count} messages scanned.\n")
    return message_count


async def run_historical_scrape(
    client: TelegramClient,
    target_groups: list[tuple[str, object]],
    users_by_key: dict[str, ScrapedUser],
    progress: dict[str, GroupProgress],
    save_tracker: SaveTracker,
) -> int:
    total_messages = 0
    skipped = 0
    for index, (group_title, entity) in enumerate(target_groups, start=1):
        key = group_progress_key(entity)
        if progress.get(key) and progress[key].completed:
            skipped += 1
            print(f"[{index}/{len(target_groups)}] Skipping: {group_title} (done)")
            continue

        print(f"[{index}/{len(target_groups)}] ", end="")
        total_messages += await scrape_single_group(
            client,
            group_title,
            entity,
            users_by_key,
            progress,
            save_tracker,
        )

    if skipped:
        print(f"Skipped {skipped} already-completed group(s).")
    return total_messages


async def run_live_monitor(
    client: TelegramClient,
    target_groups: list[tuple[str, object]],
    users_by_key: dict[str, ScrapedUser],
    save_tracker: SaveTracker,
) -> None:
    title_map = build_group_title_map(target_groups)
    chat_entities = [entity for _, entity in target_groups]
    save_lock = asyncio.Lock()
    sender_cache: dict[int, User] = {}

    async def on_new_message(event: events.NewMessage.Event) -> None:
        try:
            chat_id = utils.get_peer_id(event.chat_id)
            group_title = title_map.get(chat_id)
            if not group_title:
                chat = await event.get_chat()
                group_title = getattr(chat, "title", None) or str(chat_id)

            new_users = await process_message(
                event.message, group_title, users_by_key, sender_cache
            )
            if not new_users:
                return

            async with save_lock:
                save_tracker.maybe_save_usernames(force=True)

            for user in new_users:
                print(
                    f"+ NEW @{user.username}  from: {group_title}  "
                    f"[total: {len(users_by_key)}]"
                )
        except FloodWaitError as exc:
            print(f"Rate limit — waiting {exc.seconds}s...")
            await asyncio.sleep(exc.seconds + 1)
        except Exception as exc:
            print(f"Error processing message: {exc}")

    client.add_event_handler(on_new_message, events.NewMessage(chats=chat_entities))

    print("=" * 60)
    print("LIVE MODE — watching for new messages")
    print(f"  Monitoring {len(chat_entities)} group(s)")
    print(f"  Master file: {MASTER_JSON}")
    print("  Press Ctrl+C to stop")
    print("=" * 60 + "\n")

    stop_event = asyncio.Event()

    def request_stop(*_args: object) -> None:
        if not stop_event.is_set():
            print("\nStopping live monitor...")
            stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, request_stop)
        except NotImplementedError:
            signal.signal(sig, request_stop)

    client_task = asyncio.create_task(client.run_until_disconnected())
    stop_task = asyncio.create_task(stop_event.wait())

    done, pending = await asyncio.wait(
        {client_task, stop_task},
        return_when=asyncio.FIRST_COMPLETED,
    )

    for task in pending:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    client.remove_event_handler(on_new_message)
    await client.disconnect()


async def scrape_group_usernames(live: bool) -> list[ScrapedUser]:
    validate_config()

    users_by_key = load_master_users()
    progress = load_progress()
    save_tracker = SaveTracker(users_by_key, progress)

    if users_by_key:
        batch_count = sync_batch_exports(users_by_key)
        print(f"Loaded {len(users_by_key)} existing username(s) from {MASTER_JSON}")
        print(f"Batch exports: {batch_count} file(s) in {EXPORTS_DIR}/\n")
    if progress:
        done_count = sum(1 for g in progress.values() if g.completed)
        if done_count:
            print(f"Loaded progress: {done_count} group(s) already completed")
    print()

    client = TelegramClient(SESSION_NAME, int(API_ID), API_HASH)
    connected = False

    try:
        try:
            await client.connect()
            connected = True
        except Exception as exc:
            if "database is locked" in str(exc).lower():
                print("\nERROR: Session file is locked.")
                print("Another bot instance is already running.")
                print("Fix: close all other terminals running scrape_usernames.py,")
                print("     or end python.exe / python3.13 in Task Manager, then try again.\n")
            raise SystemExit(1) from exc

        if not await client.is_user_authorized():
            if PHONE_NUMBER:
                print(f"Logging in with phone from .env: {PHONE_NUMBER}")
                await client.start(phone=PHONE_NUMBER)
            else:
                await client.start()

        print("Connecting to Telegram...")
        me = await client.get_me()
        print(f"Logged in as: {me.first_name} (@{me.username or 'no username'})\n")

        target_groups = await resolve_target_groups(client)
        if not target_groups:
            print("No groups to scrape. Check GROUP_TARGETS in your .env file.")
            raise SystemExit(1)

        if live and LIVE_SCRAPE_HISTORY:
            print(
                "Live mode: scanning history (resume + auto-save), "
                "then watching new messages...\n"
            )
            total_messages = await run_historical_scrape(
                client, target_groups, users_by_key, progress, save_tracker
            )
            save_tracker.maybe_save_usernames(force=True)
            print("History scan finished.")
            print(f"  Groups scanned: {len(target_groups)}")
            print(f"  Messages scanned: {total_messages}")
            print(f"  Unique usernames: {len(users_by_key)}")
            print(f"  Saved to: {MASTER_JSON}\n")
            await run_live_monitor(client, target_groups, users_by_key, save_tracker)
        elif live:
            save_tracker.maybe_save_usernames(force=True)
            print("Live mode: skipping history (LIVE_SCRAPE_HISTORY=false)")
            print(f"  Starting from {len(users_by_key)} known username(s)")
            print(f"  Master file: {MASTER_JSON}\n")
            await run_live_monitor(client, target_groups, users_by_key, save_tracker)
        else:
            total_messages = await run_historical_scrape(
                client, target_groups, users_by_key, progress, save_tracker
            )
            save_tracker.maybe_save_usernames(force=True)
            print("All groups finished.")
            print(f"  Groups scanned: {len(target_groups)}")
            print(f"  Messages scanned: {total_messages}")
            print(f"  Unique usernames: {len(users_by_key)}\n")

        if live:
            save_tracker.maybe_save_usernames(force=True)
            print(f"\nLive monitor stopped. {len(users_by_key)} username(s) in master file.")
    finally:
        if connected:
            await client.disconnect()
        save_tracker.save_on_exit()

    return sorted(users_by_key.values(), key=lambda u: u.username.lower())


def print_results(users: list[ScrapedUser]) -> None:
    if not users:
        print("No usernames found.")
        return

    print("=" * 70)
    print(f"{'#':<4} {'Username':<22} {'User ID':<14} Groups")
    print("=" * 70)

    for index, user in enumerate(users, start=1):
        groups_text = ", ".join(user.groups)
        user_id = user.user_id if user.user_id is not None else "-"
        print(f"{index:<4} @{user.username:<21} {str(user_id):<14} {groups_text}")

    print("=" * 70)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape Telegram group usernames.")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Watch groups for new messages and append new usernames (also set LIVE_MODE=true in .env)",
    )
    parser.add_argument(
        "--no-history",
        action="store_true",
        help="In live mode, skip scanning old messages and only watch new ones",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    live = args.live or LIVE_MODE

    if args.no_history:
        global LIVE_SCRAPE_HISTORY
        LIVE_SCRAPE_HISTORY = False

    users = await scrape_group_usernames(live=live)

    if not live:
        print_results(users)
        if users:
            users_dict = {u.username.lower(): u for u in users}
            master_json = save_master_users(users_dict)
            snapshot_json, snapshot_csv = save_snapshot(users_dict)
            print("\nSaved to:")
            print(f"  Master:   {master_json}")
            print(f"  Batches:  {EXPORTS_DIR}/")
            print(f"  Snapshot: {snapshot_json}")
            print(f"            {snapshot_csv}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped by user.")
