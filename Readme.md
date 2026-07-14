# Telegram Music Bot

A Telegram music bot that supports YouTube, Spotify, and local audio files.

## Features

- Play music from YouTube (search or URL)
- Play music from Spotify (track or playlist)
- Play local audio files
- Voice chat playback
- Queue management
- Pause / Resume / Skip controls

## Requirements

- Python 3.9+
- FFmpeg installed on your system
- Telegram API credentials (from my.telegram.org)
- Telegram Bot Token (from @BotFather)
- Spotify API credentials (optional, from developer.spotify.com)

## Setup

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your credentials:
   ```bash
   cp .env.example .env
   ```
4. Run the bot:
   ```bash
   python Bot.py
   ```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BOT_TOKEN` | Yes | Telegram bot token from @BotFather |
| `API_ID` | Yes | Telegram API ID from my.telegram.org |
| `API_HASH` | Yes | Telegram API hash from my.telegram.org |
| `SPOTIFY_CLIENT_ID` | No | Spotify API client ID |
| `SPOTIFY_CLIENT_SECRET` | No | Spotify API client secret |
| `OWNER_ID` | No | Telegram user ID of the bot owner |

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the bot |
| `/play <query>` | Play a song by name or URL |
| `/playfile` | Reply to an audio file to play it |
| `/pause` | Pause playback |
| `/resume` | Resume playback |
| `/stop` | Stop and clear queue |
| `/skip` | Skip current song |
| `/queue` | Show current queue |
| `/now` | Show now playing |
