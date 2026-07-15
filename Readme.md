# Shared Playlist Telegram Bot

A Telegram bot for a group chat: anyone can add songs by name or link, and
they all land in one shared playlist for the chat. No paid API keys needed —
songs are found via YouTube search.

## 1. Get a bot token

1. Open Telegram, search for **@BotFather**.
2. Send `/newbot` and follow the prompts (choose a name and a username
   ending in `bot`).
3. BotFather gives you a token like `123456789:ABCdefGhIJKlmNoPQRstuVwxyZ`.
4. Open `bot.py` and paste it in for `BOT_TOKEN`.

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

(If you get a "externally managed environment" error, add
`--break-system-packages` to the command, or use a virtual environment.)

## 3. Run it

```bash
python3 bot.py
```

Add the bot to your group chat, then in Telegram:

- `/add faded alan walker` — searches YouTube and adds it to the playlist
- `/add https://youtube.com/watch?v=...` — adds a direct link too
- `/playlist` — lists everything added so far, with who added it
- `/play 2` — sends the link for song #2
- `/remove 2` — removes song #2
- `/clear` — wipes the whole playlist

Each group chat gets its own playlist automatically (songs are stored per
`chat_id`), so if you add this bot to multiple groups they won't mix.

## 4. Keeping it running 24/7

`python3 bot.py` only runs while your terminal is open. To keep the bot
online all the time, you have two easy free-tier options:

- **Railway** or **Render**: push this folder to GitHub, connect the repo,
  set it to run `python3 bot.py` as a background worker. Put `BOT_TOKEN` in
  an environment variable instead of hardcoding it (recommended either way).
- **Your own machine / a Raspberry Pi**: run it inside `tmux` or `screen` so
  it survives closing the terminal.

## Notes

- `playlist.db` is a small SQLite file created automatically the first time
  you run the bot — that's where all the songs are stored.
- If a `/add` search doesn't find anything, try being more specific
  (song + artist name works best).