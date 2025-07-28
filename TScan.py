import os, sys, asyncio, hashlib, subprocess, aiosqlite, time, json

from pathlib import Path

import aiosqlite
from telethon import TelegramClient
from telethon.tl.types import MessageMediaDocument

from rich.console import Console, Group
from rich.text import Text
from rich.live import Live
from rich.progress import (
    Progress, SpinnerColumn, TextColumn, BarColumn,
    TransferSpeedColumn, TimeElapsedColumn, TimeRemainingColumn,
    ProgressColumn
)

# Auto-install any missing dependencies — lazy but helpful!
REQUIRED = ['telethon', 'rich', 'aiosqlite']
for pkg in REQUIRED:
    try:
        __import__(pkg if pkg != 'rich' else 'rich.console')
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

# === Load config or prompt for it ===
CONFIG_PATH = 'config.json'
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
else:
    # Ask user for credentials and store them
    config = {
        'api_id': int(input("Enter your Telegram API ID: ").strip()),
        'api_hash': input("Enter your API Hash: ").strip(),
        'source_channel': input("Source channel username: ").strip(),
        'target_channel': input("Target channel username: ").strip()
    }
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)

api_id = config['api_id']
api_hash = config['api_hash']
source_channel = config['source_channel']
target_channel = config['target_channel']

# Paths and flags
download_folder = 'downloads'
os.makedirs(download_folder, exist_ok=True)

db_path = 'uploads.db'
log_file = 'upload_log.txt'
dry_run = False
auto_delete = True
MAX_CONCURRENT_UPLOADS = 3
UPLOAD_DELAY = 2  # seconds between uploads

client = TelegramClient('session_name', api_id, api_hash)
console = Console()

# === Progress UI setup ===
def format_bytes(size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"

class MBColumn(ProgressColumn):
    def render(self, task):
        mb_done = task.completed / (1024 * 1024)
        mb_total = task.total / (1024 * 1024) if task.total else 0
        return Text(f"{mb_done:.2f}/{mb_total:.2f} MB")

class DynamicSizeColumn(ProgressColumn):
    def render(self, task):
        return Text(f"{format_bytes(task.completed)}/{format_bytes(task.total)}")

main_progress = Progress(
    SpinnerColumn(),
    TextColumn("[bold green]{task.description}"),
    BarColumn(),
    DynamicSizeColumn(),
    TransferSpeedColumn(),
    TimeRemainingColumn(),
    TimeElapsedColumn(),
    transient=False,
    console=console
)

file_progress = Progress(
    SpinnerColumn(),
    TextColumn("[cyan]{task.description}"),
    BarColumn(),
    MBColumn(),
    TransferSpeedColumn(),
    TimeRemainingColumn(),
    TimeElapsedColumn(),
    transient=False,
    console=console
)

# === Helpers ===
def log(text):
    console.print(text)
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(text + '\n')

def get_safe_file_key(msg):
    return msg.file.name or f"{msg.id}{msg.file.ext or ''}"

async def get_sha1(file_path):
    h = hashlib.sha1()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

async def init_db():
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS uploads (
            file_key TEXT PRIMARY KEY,
            file_size INTEGER,
            file_hash TEXT,
            status TEXT,
            error TEXT
        )""")
        await db.commit()

async def is_already_uploaded(file_key, size, sha1):
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT 1 FROM uploads WHERE file_key = ? OR (file_size = ? AND file_hash = ?)",
            (file_key, size, sha1)
        )
        return await cursor.fetchone() is not None

async def record_upload(file_key, size, sha1, status, error=None):
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT OR REPLACE INTO uploads VALUES (?, ?, ?, ?, ?)",
            (file_key, size, sha1, status, error)
        )
        await db.commit()

async def scan_channel(channel_name):
    found = []
    async for msg in client.iter_messages(channel_name, limit=None):
        if isinstance(msg.media, MessageMediaDocument) and msg.file:
            found.append((get_safe_file_key(msg), msg))
    return found

async def tail_file(path, stop_event, task_id, total_size, interval=0.5):
    last_size = 0
    while not stop_event.is_set():
        if os.path.exists(path):
            current_size = os.path.getsize(path)
            if current_size > last_size:
                file_progress.update(task_id, completed=current_size)
                last_size = current_size
                if current_size >= total_size:
                    stop_event.set()
                    break
        await asyncio.sleep(interval)

async def upload_worker(msg, semaphore, main_task_id, summary):
    async with semaphore:
        key = get_safe_file_key(msg)
        size = msg.file.size or 1
        name = msg.file.name or f"{msg.id}{msg.file.ext or ''}"
        path = os.path.join(download_folder, name)

        main_progress.update(main_task_id, total=main_progress.tasks[main_task_id].total + size)

        download_task = file_progress.add_task(f"Downloading: {name}", total=size)
        stop_event = asyncio.Event()
        tail_task = asyncio.create_task(tail_file(path, stop_event, download_task, size))

        try:
            await msg.download_media(file=path)
            stop_event.set()
            await tail_task
            file_progress.remove_task(download_task)

            actual_size = os.path.getsize(path)
            sha1 = await get_sha1(path)

            if await is_already_uploaded(key, actual_size, sha1):
                log(f"[⏩] Already uploaded: {name}")
                if auto_delete: os.remove(path)
                main_progress.update(main_task_id, advance=actual_size)
                return

            if dry_run:
                log(f"[🧪] Would upload: {name}")
                await record_upload(key, actual_size, sha1, "dry_run")
                if auto_delete: os.remove(path)
                main_progress.update(main_task_id, advance=actual_size)
                return

            await asyncio.sleep(UPLOAD_DELAY)

            upload_task = file_progress.add_task(f"Uploading: {name}", total=actual_size)

            async def progress_cb(sent, _):
                file_progress.update(upload_task, completed=sent)

            await client.send_file(
                target_channel, path, caption=msg.text or "", progress_callback=progress_cb
            )

            file_progress.remove_task(upload_task)
            log(f"[📤] Uploaded: {name}")
            await record_upload(key, actual_size, sha1, "uploaded")
            summary['total_files'] += 1
            summary['total_size'] += actual_size

            if auto_delete:
                os.remove(path)

        except Exception as e:
            stop_event.set()
            await tail_task
            file_progress.remove_task(download_task)
            log(f"[❌] Failed: {name} — {e}")
            await record_upload(key, 0, "?", "error", str(e))
        finally:
            main_progress.update(main_task_id, advance=size)

async def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    await init_db()
    await client.start()
    console.rule("[bold cyan]Sanction Reuploader")

    log("[🔍] Scanning source channel...")
    messages = await scan_channel(source_channel)
    total_files = len(messages)
    total_size = sum(msg.file.size or 0 for _, msg in messages)

    log(f"[📦] Found {total_files} files ({format_bytes(total_size)})")

    task_id = main_progress.add_task("Processing...", total=0)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_UPLOADS)
    summary = {"total_files": 0, "total_size": 0, "start": time.time()}

    with Live(Group(main_progress, file_progress), refresh_per_second=10, console=console):
        await asyncio.gather(*[
            upload_worker(msg, semaphore, task_id, summary)
            for _, msg in messages
        ])

    summary["end"] = time.time()
    duration = summary["end"] - summary["start"]
    speed = format_bytes(summary["total_size"] / duration) if duration else "0 B/s"

    log(f"[✅] Done. Uploaded {summary['total_files']} files in {duration:.1f}s ({speed})")
    await client.disconnect()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("[red]\nInterrupted by user.[/red]")
