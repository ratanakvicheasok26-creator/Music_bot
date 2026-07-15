"""
Telegram Music Playlist Bot
----------------------------
A polished group-friendly bot that lets anyone in a chat add songs to a shared
playlist by name or link. Songs are resolved via YouTube search (no paid API
keys needed) and stored in a local SQLite database.
"""

import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes

import yt_dlp
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DB_PATH = Path(__file__).resolve().parent / "playlist.db"
PAGE_SIZE = 10

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

HELP_TEXT = (
    "🎵 Playlist Bot Commands\n\n"
    "/add <song or link> - search YouTube and add a song\n"
    "/playlist [page] - view the playlist (10 songs per page)\n"
    "/play <number> - get the link for a song by number\n"
    "/remove <number> - remove a song by number\n"
    "/stats - show playlist summary\n"
    "/clear - clear the whole playlist\n"
    "/help - show this help"
)

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Create the songs table if it doesn't already exist."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS songs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                added_by TEXT NOT NULL,
                added_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def add_song_to_db(chat_id: int, title: str, url: str, added_by: str) -> tuple[bool, str]:
    with sqlite3.connect(DB_PATH) as conn:
        existing = conn.execute(
            "SELECT 1 FROM songs WHERE chat_id = ? AND url = ? LIMIT 1",
            (chat_id, url),
        ).fetchone()
        if existing is not None:
            return False, "duplicate"

        conn.execute(
            "INSERT INTO songs (chat_id, title, url, added_by, added_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (chat_id, title, url, added_by, datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
        return True, "added"


def get_playlist(chat_id: int, page: int = 1, page_size: int = PAGE_SIZE) -> list[tuple]:
    if page < 1:
        page = 1
    offset = (page - 1) * page_size
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT id, title, url, added_by FROM songs WHERE chat_id = ? ORDER BY id LIMIT ? OFFSET ?",
            (chat_id, page_size, offset),
        )
        return cur.fetchall()


def get_playlist_count(chat_id: int) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT COUNT(*) FROM songs WHERE chat_id = ?", (chat_id,))
        return int(cur.fetchone()[0])


def get_playlist_stats(chat_id: int) -> dict[str, object]:
    with sqlite3.connect(DB_PATH) as conn:
        total = int(
            conn.execute("SELECT COUNT(*) FROM songs WHERE chat_id = ?", (chat_id,)).fetchone()[0]
        )
        latest = conn.execute(
            "SELECT title, added_by FROM songs WHERE chat_id = ? ORDER BY id DESC LIMIT 1",
            (chat_id,),
        ).fetchone()
        top_contributor = conn.execute(
            "SELECT added_by, COUNT(*) FROM songs WHERE chat_id = ? GROUP BY added_by "
            "ORDER BY COUNT(*) DESC LIMIT 1",
            (chat_id,),
        ).fetchone()

    return {
        "total": total,
        "latest_title": latest[0] if latest else None,
        "latest_added_by": latest[1] if latest else None,
        "top_contributor": top_contributor[0] if top_contributor else None,
        "top_contributor_count": top_contributor[1] if top_contributor else 0,
    }


def get_song_by_position(chat_id: int, position: int) -> tuple | None:
    """Songs are shown to users as 1, 2, 3... rather than raw DB ids."""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT id, title, url, added_by FROM songs WHERE chat_id = ? ORDER BY id",
            (chat_id,),
        )
        songs = cur.fetchall()

    if 1 <= position <= len(songs):
        return songs[position - 1]
    return None


def remove_song_by_position(chat_id: int, position: int) -> str | None:
    song = get_song_by_position(chat_id, position)
    if song is None:
        return None
    song_id, title, _url, _added_by = song
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM songs WHERE id = ?", (song_id,))
        conn.commit()
    return title


def clear_playlist(chat_id: int) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("DELETE FROM songs WHERE chat_id = ?", (chat_id,))
        conn.commit()
        return cur.rowcount


# ---------------------------------------------------------------------------
# YouTube search (no API key required)
# ---------------------------------------------------------------------------

YDL_SEARCH_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch1",
    "skip_download": True,
}


def resolve_song(query: str) -> tuple[str, str] | None:
    """
    Given a song name or a direct YouTube link, return (title, url).
    Returns None if nothing was found.
    """
    with yt_dlp.YoutubeDL(YDL_SEARCH_OPTS) as ydl:
        try:
            info = ydl.extract_info(query, download=False)
        except Exception as e:  # noqa: BLE001
            logger.warning("yt-dlp lookup failed for %r: %s", query, e)
            return None

    if info is None:
        return None

    if "entries" in info:
        entries = [e for e in info["entries"] if e]
        if not entries:
            return None
        info = entries[0]

    title = info.get("title", "Unknown title")
    url = info.get("webpage_url") or info.get("url")
    if not url:
        return None
    return title, url


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🎵 Welcome to the shared playlist bot!\n\n"
        "Everyone in this chat can add songs to one shared playlist.\n\n"
        "Use /add <song name or link> to contribute a track.\n"
        "Use /playlist to browse the queue and /stats for a quick summary."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT)


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /add <song name or YouTube link>")
        return

    query = " ".join(context.args)
    chat_id = update.effective_chat.id
    user = update.effective_user.first_name or "Unknown"

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    result = resolve_song(query)

    if result is None:
        await update.message.reply_text(
            f"❌ Couldn't find a match for: {query}\nTry a more specific title or a direct YouTube URL."
        )
        return

    title, url = result
    added, status = add_song_to_db(chat_id, title, url, user)
    if not added:
        await update.message.reply_text("🎵 This song is already in the playlist for this chat.")
        return

    position = get_playlist_count(chat_id)
    await update.message.reply_text(
        f"✅ Added #{position}: {title}\n{url}\n(added by {user})"
    )


async def playlist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    page = 1
    if context.args and context.args[0].isdigit():
        page = max(1, int(context.args[0]))

    songs = get_playlist(chat_id, page=page)
    total = get_playlist_count(chat_id)
    if not songs:
        await update.message.reply_text("The playlist is empty. Add one with /add <song>!")
        return

    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    lines = [f"🎶 Shared Playlist • Page {page}/{total_pages} • {total} song(s)"]
    start_number = (page - 1) * PAGE_SIZE + 1
    for offset, (_id, title, _url, added_by) in enumerate(songs, start=start_number):
        lines.append(f"{offset}. {title} — added by {added_by}")

    if page < total_pages:
        lines.append("\nUse /playlist 2 for the next page.")

    await update.message.reply_text("\n".join(lines))


async def play(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /play <number>  (see /playlist for numbers)")
        return

    chat_id = update.effective_chat.id
    position = int(context.args[0])
    song = get_song_by_position(chat_id, position)

    if song is None:
        await update.message.reply_text("No song at that number. Check /playlist.")
        return

    _id, title, url, _added_by = song
    await update.message.reply_text(f"▶️ {title}\n{url}")


async def remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /remove <number>  (see /playlist for numbers)")
        return

    chat_id = update.effective_chat.id
    position = int(context.args[0])
    title = remove_song_by_position(chat_id, position)

    if title is None:
        await update.message.reply_text("No song at that number. Check /playlist.")
        return

    await update.message.reply_text(f"🗑️ Removed: {title}")


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    count = clear_playlist(chat_id)
    await update.message.reply_text(f"🧹 Cleared {count} song(s) from the playlist.")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    summary = get_playlist_stats(chat_id)

    lines = ["📊 Playlist summary"]
    lines.append(f"Total songs: {summary['total']}")
    if summary["latest_title"]:
        lines.append(f"Latest: {summary['latest_title']}")
        lines.append(f"Added by: {summary['latest_added_by']}")
    if summary["top_contributor"]:
        lines.append(
            f"Top contributor: {summary['top_contributor']} ({summary['top_contributor_count']} song(s))"
        )
    if summary["total"] == 0:
        lines.append("The playlist is empty right now.")

    await update.message.reply_text("\n".join(lines))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is missing. Set it as an environment variable before starting the bot.")
        raise SystemExit(1)

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("playlist", playlist))
    app.add_handler(CommandHandler("play", play))
    app.add_handler(CommandHandler("remove", remove))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("stats", stats))

    logger.info("Bot starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
