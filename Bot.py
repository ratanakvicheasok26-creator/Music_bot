"""
Telegram Music Playlist Bot
----------------------------
A group-friendly bot that lets anyone in a chat add songs to a shared
playlist by name or link. Songs are resolved via YouTube search (no paid
API keys needed) and stored in a local SQLite database.

Commands:
    /start              - Welcome message and quick help
    /add <song or link> - Add a song to the shared playlist
    /playlist           - Show the current playlist
    /play <number>      - Get the link (and optionally audio) for a song
    /remove <number>    - Remove a song from the playlist
    /clear              - Clear the entire playlist
    /help               - Show usage instructions
"""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

import yt_dlp

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BOT_TOKEN = "8916132863:AAF5emgOUupA-dB3GJ0h3aQKLB_yqB2qLqg"  # from @BotFather
DB_PATH = Path(__file__).parent / "playlist.db"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

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


def add_song_to_db(chat_id: int, title: str, url: str, added_by: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO songs (chat_id, title, url, added_by, added_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (chat_id, title, url, added_by, datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()


def get_playlist(chat_id: int) -> list[tuple]:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT id, title, url, added_by FROM songs WHERE chat_id = ? ORDER BY id",
            (chat_id,),
        )
        return cur.fetchall()


def get_song_by_position(chat_id: int, position: int) -> tuple | None:
    """Songs are shown to users as 1, 2, 3... rather than raw DB ids."""
    songs = get_playlist(chat_id)
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

    # If it was a search, yt-dlp wraps results in an "entries" list
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
        "/add <song name or link> - add a song\n"
        "/playlist - see the current playlist\n"
        "/play <number> - get the link for a song\n"
        "/remove <number> - remove a song\n"
        "/clear - clear the whole playlist\n"
        "/help - show this again"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start(update, context)


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /add <song name or YouTube link>")
        return

    query = " ".join(context.args)
    chat_id = update.effective_chat.id
    user = update.effective_user.first_name

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    result = resolve_song(query)

    if result is None:
        await update.message.reply_text(f"❌ Couldn't find a match for: {query}")
        return

    title, url = result
    add_song_to_db(chat_id, title, url, user)
    position = len(get_playlist(chat_id))
    await update.message.reply_text(
        f"✅ Added #{position}: {title}\n{url}\n(added by {user})"
    )


async def playlist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    songs = get_playlist(chat_id)

    if not songs:
        await update.message.reply_text("The playlist is empty. Add one with /add <song>!")
        return

    lines = ["🎶 Shared Playlist:"]
    for i, (_id, title, _url, added_by) in enumerate(songs, start=1):
        lines.append(f"{i}. {title} — added by {added_by}")
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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("playlist", playlist))
    app.add_handler(CommandHandler("play", play))
    app.add_handler(CommandHandler("remove", remove))
    app.add_handler(CommandHandler("clear", clear))

    logger.info("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()