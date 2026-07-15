# Telegram Shared Playlist Bot

A group-friendly Telegram bot that lets anyone in a chat add songs to a shared playlist. Songs are found via YouTube search — no paid API keys needed.

## Features

- **Add by name or link** — search YouTube or paste a direct URL
- **Per-group playlists** — each chat gets its own isolated playlist
- **Duplicate detection** — the same song can't be added twice
- **Pagination** — browse large playlists 10 songs at a time
- **Stats** — see total songs, top contributor, and latest addition
- **SQLite storage** — lightweight, zero-config database

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and quick overview |
| `/add <song or link>` | Search YouTube and add a song |
| `/playlist [page]` | View the playlist (10 per page) |
| `/play <number>` | Get the link for a song by position |
| `/remove <number>` | Remove a song by position |
| `/stats` | Playlist summary |
| `/clear` | Wipe the entire playlist |
| `/help` | Show all commands |

## Quick Start

### 1. Create a bot token

1. Open Telegram and message **@BotFather**.
2. Send `/newbot` and follow the prompts.
3. Copy the token BotFather gives you.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

`ffmpeg` is also required by `yt-dlp` for audio extraction:

```bash
# Ubuntu / Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

### 3. Configure environment

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|----------|----------|-------------|
| `BOT_TOKEN` | Yes | Telegram bot token from BotFather |

### 4. Run

```bash
export BOT_TOKEN="your-token-here"
python3 Bot.py
```

Or with a `.env` file:

```bash
python3 Bot.py
```

Add the bot to your group chat and start adding songs.

## Deployment

### Railway

This project is ready to deploy on [Railway](https://railway.app):

1. Push this repo to GitHub.
2. Go to [railway.app](https://railway.app) and create a new project.
3. Connect your GitHub repo.
4. Railway auto-detects the `nixpacks.toml` and `Procfile` — no config needed.
5. Add the `BOT_TOKEN` environment variable in Railway's dashboard.
6. Deploy.

### Render

1. Create a new **Background Worker** on [Render](https://render.com).
2. Connect your repo.
3. Render picks up the `Procfile` automatically.
4. Set the `BOT_TOKEN` env var.
5. Deploy.

### Self-hosted

Run with `tmux` or `screen` for persistence:

```bash
tmux new -s musicbot
python3 Bot.py
# Ctrl+B, D to detach
```

## Project Structure

```
Music_bot/
├── Bot.py            # Bot logic, handlers, and database
├── requirements.txt  # Python dependencies
├── .env.example      # Environment variable template
├── nixpacks.toml     # Railway deployment config
├── Procfile          # Process declaration (Render / Heroku)
└── playlist.db       # SQLite database (created on first run)
```

## How It Works

1. A user sends `/add <query>` in a group chat.
2. The bot uses `yt-dlp` to search YouTube (`ytsearch1`) and resolve the first result to a title + URL.
3. The song is inserted into a per-chat SQLite table with the song title, URL, who added it, and a timestamp.
4. Duplicate URLs are rejected before insertion.
5. All other commands (`/playlist`, `/play`, `/remove`, `/stats`, `/clear`) query the same SQLite table filtered by `chat_id`.

## Troubleshooting

**Bot doesn't respond to messages**
- Make sure the bot is added to the group as a member (not just an admin).
- Check that `BOT_TOKEN` is set correctly.

**/add returns "Couldn't find a match"**
- Try a more specific query (e.g. `Bohemian Rhapsody Queen` instead of just `Bohemian Rhapsody`).
- Paste a full YouTube URL instead of searching by name.

**Songs disappear after restart**
- The `playlist.db` file persists data. If it's missing, check that your working directory is the project root.

**Deployment fails with "ffmpeg not found"**
- Make sure `ffmpeg` is installed. On Railway, `nixpacks.toml` handles this automatically.

## License

MIT
