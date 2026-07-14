import os
import asyncio
import logging
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import yt_dlp

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

ydl_opts = {
    "format": "bestaudio[ext=m4a]/bestaudio/best",
    "postprocessors": [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }
    ],
    "outtmpl": "downloads/%(id)s.%(ext)s",
    "quiet": True,
    "no_warnings": True,
    "extractor_retries": 3,
    "retries": 3,
    "writethumbnail": False,
    "ignoreerrors": True,
    "socket_timeout": 30,
}

os.makedirs("downloads", exist_ok=True)


def download_track(url):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if info is None:
            raise Exception("Failed to extract info from URL")
        if "id" not in info:
            raise Exception("No video ID found in info")
        base = os.path.join("downloads", info["id"])
        mp3_file = base + ".mp3"
        if os.path.exists(mp3_file):
            return mp3_file, info.get("title", "Unknown"), info.get("duration", 0)
        for ext in ["m4a", "webm", "ogg", "mp4"]:
            candidate = base + "." + ext
            if os.path.exists(candidate):
                return candidate, info.get("title", "Unknown"), info.get("duration", 0)
        raise FileNotFoundError(f"Downloaded file not found for {info['id']}")


def is_youtube_url(text):
    return "youtube.com" in text or "youtu.be" in text


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 **YouTube Audio Bot**\n\n"
        "Send me a YouTube URL and I'll download it as audio.\n\n"
        "**How to use:**\n"
        "- Send `/play <YouTube URL>`\n"
        "- Or just paste a YouTube URL directly",
        parse_mode="Markdown",
    )


async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        url = " ".join(context.args).strip()
    elif update.message and update.message.text:
        parts = update.message.text.split(maxsplit=1)
        url = parts[1].strip() if len(parts) > 1 else ""
    else:
        return

    if not url:
        await update.message.reply_text("Please provide a YouTube URL.")
        return

    if not is_youtube_url(url):
        await update.message.reply_text("Please provide a valid YouTube URL.")
        return

    status_msg = await update.message.reply_text("⬇️ Downloading...")

    try:
        file_path, title, duration = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, download_track, url),
            timeout=120,
        )

        with open(file_path, "rb") as audio_file:
            await context.bot.send_voice(
                chat_id=update.effective_chat.id,
                voice=audio_file,
                duration=duration,
            )

        try:
            os.remove(file_path)
        except OSError:
            pass

        await status_msg.edit_text(f"✅ Done: {title}")

    except Exception as e:
        logger.error(f"Error: {e}")
        await status_msg.edit_text(f"❌ Error: {str(e)}")


async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    if is_youtube_url(text):
        context.args = [text]
        await play(update, context)


def main():
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN not set.")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CommandHandler("play", play))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))

    print("🎵 Bot started!")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        poll_interval=2,
        timeout=30,
        bootstrap_retries=5,
    )


if __name__ == "__main__":
    main()
