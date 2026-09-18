# AutoAnimeBot

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Tests](https://github.com/kaif-00z/AutoAnimeBot/actions/workflows/ci.yml/badge.svg)](https://github.com/kaif-00z/AutoAnimeBot/actions/workflows/ci.yml)
[![Code Quality](https://github.com/kaif-00z/AutoAnimeBot/actions/workflows/pylint.yml/badge.svg)](https://github.com/kaif-00z/AutoAnimeBot/actions/workflows/pylint.yml)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](Dockerfile)

> **Auto-download, encode (HEVC/libx265), and upload ongoing anime from SubsPlease to Telegram — fully automated.**

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Auto-download** | Fetches new episodes from SubsPlease via magnets (aria2c) |
| **HEVC Encoding** | Compresses to libx265 with configurable CRF (20–51) + progress bar |
| **Multi-quality** | 480p, 720p, 1080p — all handled automatically |
| **Smart upload** | Pyrogram for >2GB files, Telethon for metadata & buttons |
| **Separate channels** | Creates per-anime channels with invite links (requires `SESSION`) |
| **Button upload** | File-store style: episode buttons → backup channel (10-min auto-delete) |
| **Screenshots & MediaInfo** | Auto-generates 10 screenshots + sample clip + MediaInfo telegraph page |
| **Force Subscribe** | Require users to join a channel before using the bot |
| **Broadcast** | Admin can broadcast messages to all users |
| **Daily schedule** | Posts airing schedule at 00:30 IST (optional) |
| **Admin panel** | Inline keyboard to toggle features at runtime |
| **MongoDB state** | Tracks uploaded episodes, channel info, user broadcasts, options |

---

## 🏗 Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│  SubsPlease RSS │────▶│  Torrent DL  │────▶│  FFmpeg     │
│  (magnet links) │     │  (aria2c)    │     │  (libx265)  │
└─────────────────┘     └──────────────┘     └──────┬──────┘
                                                     │
┌─────────────────┐     ┌──────────────┐            ▼
│  MongoDB        │◀───│  Executors   │────▶┌─────────────┐
│  (state, opts)  │     │  (encode,    │     │  Telegram   │
└─────────────────┘     │   upload)    │     │  (Pyrogram  │
                        └──────────────┘     │  + Telethon)│
                                             └─────────────┘
```

**Clients:**
- **Telethon (bot)** — commands, callbacks, metadata, progress updates
- **Telethon (user)** — channel creation, invite links (needs `SESSION`)
- **Pyrogram** — large file uploads (>2GB support)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- FFmpeg with libx265 support
- mediainfo, aria2c
- MongoDB (Atlas or self-hosted)
- Telegram API credentials ([my.telegram.org](https://my.telegram.org))
- Bot token ([@BotFather](https://t.me/BotFather))

### 1. Clone & Configure
```bash
git clone https://github.com/kaif-00z/AutoAnimeBot.git
cd AutoAnimeBot
cp .sample.env .env
nano .env   # fill in all REQUIRED variables
```

### 2. Run with Docker (Recommended)
```bash
docker build -t autoanimebot .
docker run -d --name autoanimebot --env-file .env autoanimebot
```

### 3. Run on VPS (Native)
```bash
# Install deps (Ubuntu/Debian)
sudo apt update && sudo apt install -y ffmpeg mediainfo aria2 python3-pip

# Install Python deps
pip install -r requirements.txt

# Run
python3 bot.py
```

### 4. Deploy to Heroku
[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/kaif-00z/AutoAnimeBot)

> ⚠️ Heroku: Use **Performance-M** or higher dyno. Encoding takes ~20 min/episode on basic dynos. Set `RESTART_EVERDAY=False`.

---

## ⚙️ Configuration

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `API_ID` | Telegram API ID | `123456` |
| `API_HASH` | Telegram API Hash | `abcdef123456` |
| `BOT_TOKEN` | Bot token from @BotFather | `123456:ABC-DEF...` |
| `MONGO_SRV` | MongoDB connection string | `mongodb+srv://user:pass@cluster.mongodb.net` |
| `MAIN_CHANNEL` | Main upload channel ID | `-1001234567890` |
| `LOG_CHANNEL` | Log channel ID | `-1001234567891` |
| `CLOUD_CHANNEL` | Screenshots/samples channel | `-1001234567892` |
| `BACKUP_CHANNEL` | Button upload backup channel | `-1001234567893` |
| `OWNER` | Your Telegram user ID | `123456789` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SESSION` | — | Telethon string session (for separate channels) |
| `FORCESUB_CHANNEL` | — | Force-sub channel ID |
| `FORCESUB_CHANNEL_LINK` | — | Force-sub channel invite link |
| `THUMBNAIL` | Graph.org image | Default thumbnail URL |
| `FFMPEG` | `ffmpeg` | Custom ffmpeg binary path |
| `CRF` | `27` | Encoding quality (20–51, lower = better) |
| `SEND_SCHEDULE` | `False` | Post daily schedule at 00:30 IST |
| `RESTART_EVERDAY` | `True` | Restart daily at 02:01 IST |
| `LOG_ON_MAIN` | `False` | Send logs to MAIN_CHANNEL |
| `DEV_MODE` | `False` | Use more CPU threads for encoding |

> **Get Channel IDs:** Forward a message from the channel to [@userinfobot](https://t.me/userinfobot)

---

## 📖 Usage

### User Commands

| Command | Description |
|---------|-------------|
| `/start` | Shows welcome message (owner sees admin panel) |
| `/start <msg_id>` | Retrieves file from backup channel (button upload) |
| `/start <hash>` | Retrieves screenshots & sample (hash from button) |
| `/about` | Shows bot stats & system info |
- 📜 **LOGS** — View recent log file
- ♻️ **Restart** — Graceful restart
- 🎞️ **Encode Toggle** — Switch between original upload / HEVC encode
- 📸 **SS Toggle** — Enable/disable screenshots & MediaInfo
- 🔘 **Button Upload Toggle** — File-store style upload
- 🗃️ **Separate Channel Toggle** — Per-anime channels (needs `SESSION`)
- 🔊 **Broadcast** — Send message to all users

---

## 🔧 Development

### Run Tests
```bash
pip install pytest pytest-asyncio
python -m pytest tests/ -v
```

### Verify Imports
```bash
API_ID=123456 API_HASH=abcdef BOT_TOKEN=123:abc MONGO_SRV=mongodb://localhost MAIN_CHANNEL=-100 LOG_CHANNEL=-100 CLOUD_CHANNEL=-100 BACKUP_CHANNEL=-100 OWNER=123 python -c "
import sys
sys.path.insert(0, '.')
from core.bot import Bot
from functions.tools import Tools
from functions.config import Var
from database import DataBase
from libs.kitsu import RawAnimeInfo
from libs.ariawarp import Torrent
from functions.schedule import ScheduleTasks
from functions.info import AnimeInfo
print('All imports successful!')
```

### Lint & Format
```bash
pip install black isort autoflake pylint
black --line-length 120 .
isort --profile black --line-length 120 .
autoflake --recursive --remove-all-unused-imports --remove-unused-variables .
pylint --rcfile=pylint.rc core/ functions/ libs/ database/ bot.py
```

### Project Structure
```
AutoAnimeBot/
├── bot.py                 # Entry point, event handlers
├── core/
│   ├── bot.py             # TelegramClient wrapper (Telethon + Pyrogram + user)
│   └── executors.py       # Encoding & upload orchestration
├── functions/
│   ├── config.py          # Environment config (Var class)
│   ├── tools.py           # FFmpeg, mediainfo, telegraph, HTTP, fs utils
│   ├── info.py            # Anime metadata (anitopy + Kitsu + AniList)
│   ├── schedule.py        # APScheduler jobs (schedule, restart)
│   └── utils.py           # Admin panel, broadcast, about
├── database/
│   └── __init__.py        # MongoDB (motor) collections & indexes
├── libs/
│   ├── kitsu.py           # Kitsu + AniList API client (pooled) — class: RawAnimeInfo
│   ├── ariawarp.py        # aria2c wrapper (secure)
│   └── logger.py          # Logging + Reporter (progress messages)
├── tests/
│   └── test_tools.py      # Unit tests (30+)
├── .github/workflows/     # CI: test, lint, docker build
├── Dockerfile             # Multi-stage build
├── requirements.txt       # Python deps
└── .sample.env            # Documented environment template
```

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| `ApiIdInvalidError` | Check `API_ID`/`API_HASH` match my.telegram.org |
| `AccessTokenInvalidError` | Regenerate `BOT_TOKEN` from @BotFather |
| `String session expired` | Generate new `SESSION` (see below) |
| `mediainfo not found` | `sudo apt install mediainfo` |
| `aria2c not found` | `sudo apt install aria2` |
| Encoding fails | Check FFmpeg has libx265: `ffmpeg -encoders \| grep libx265` |
| MongoDB timeout | Whitelist IP in Atlas; check `MONGO_SRV` format |
| FloodWait errors | Bot handles automatically; check `LOG_CHANNEL` |

### Generate Telethon Session String
```bash
python3 -c "
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
api_id = 123456  # YOUR API_ID
api_hash = 'your_api_hash'
with TelegramClient(StringSession(), api_id, api_hash) as client:
    print(client.session.save())
"
```

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests & lint (`pytest tests/ && black --check .`)
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push & open a PR

> **Ideas:** See [Issues](https://github.com/kaif-00z/AutoAnimeBot/issues) or improve test coverage, add AniList GraphQL metadata, migrate to yt-dlp for downloads.

---

## 📄 License

GPLv3 — see [LICENSE](LICENSE).

---

## 🙏 Credits

- [SubsPlease](https://subsplease.org/) — source of anime releases
- [Kitsu.io](https://kitsu.io/) & [AniList](https://anilist.co/) — metadata APIs
- [Pyrogram](https://pyrogram.org/) & [Telethon](https://telethon.dev/) — Telegram clients
- [FFmpeg](https://ffmpeg.org/) — encoding backbone

---

## ⭐ Support

If this project helps you, consider giving it a ⭐ on GitHub!

[![Donate](https://img.shields.io/badge/Donate-Telegram-blue?logo=telegram)](https://t.me/kaif_00z)