# Purrfect Facts - AI Cat Video Agent

Fully automated YouTube Shorts pipeline that generates, assembles, and uploads cat fact videos — no human intervention needed.

**Channel:** [Purrfect Facts](https://www.youtube.com/@PurrfectFacts)

## What It Does

One command generates a complete YouTube Short:

1. **Script** — AI writes educational cat facts with short, punchy captions (3-5 words)
2. **Footage** — Finds and downloads matching stock footage from Pexels (never repeats clips)
3. **Assembly** — FFmpeg stitches clips with text overlays, hook intro, flash transitions, and background music
4. **Thumbnail** — Auto-generates from Pexels photos
5. **Upload** — Publishes directly to YouTube via API
6. **Notify** — Sends Telegram notification on success/failure

## Architecture

```
agent.py                 # CLI entry point — orchestrates the full pipeline
├── script_generator.py  # Groq LLM (Llama 3.3 70B) generates scripts
├── footage_finder.py    # Pexels API search + download, anti-repeat tracking
├── video_assembler.py   # FFmpeg: normalize clips, captions, hook, music, concat
├── thumbnail_generator.py  # Pexels photo search for thumbnails
├── youtube_uploader.py  # YouTube Data API v3 OAuth upload
├── notifier.py          # Telegram Bot push notifications
├── voice_generator.py   # Edge TTS (unused — text-on-screen format works better)
└── config.py            # API keys, content formats, video settings
```

## Content Formats

The agent randomly picks from 8 viral formats:

| Format | Description |
|--------|-------------|
| `cat_facts` | Mind-blowing facts that make people go "Wait, REALLY?" |
| `cat_breeds` | Most beautiful/interesting cat breeds showcase |
| `reasons_to_get_cat` | Heartwarming reasons cats are amazing pets |
| `signs_cat_loves_you` | Cat body language decoded |
| `cat_psychology` | What cats are actually thinking |
| `cat_vs_dog` | Fun comparison — cats obviously win |
| `cat_myths` | Common myths debunked with real facts |
| `cat_tips` | Tips for cat owners |

## Anti-Spam System

YouTube flags repetitive content, so the agent tracks everything:

- **Footage** — `used_footage.json` stores all Pexels video IDs ever used (158+ clips). Every new video gets fresh footage.
- **Scripts** — `used_scripts.json` stores past titles (last 50) and captions (last 200). The LLM prompt includes "DO NOT repeat these."
- **Titles** — Enforced uniqueness: different words, angles, and structures each time.

## Video Assembly Details

Each Short is ~20-25 seconds:

- **Hook clip** (1.5s) — Eye-catching text like "Did you know?" or "Watch till the end"
- **10 content clips** (2.5s each) — Beautiful cat footage with fact captions overlaid
- **Flash transitions** (0.08s) — White flash between clips for energy
- **Background music** — 7 tracks, mood-matched to content format, with random tempo variation
- **Audio normalization** — `loudnorm` filter ensures consistent volume across all tracks
- **Dynamic captions** — Font size auto-scales based on text length (52px for short, 34px for long)

## Quick Start

### Prerequisites

- Python 3.12+
- FFmpeg (auto-detected via system PATH or `imageio-ffmpeg`)

### Install

```bash
git clone https://github.com/andiboi69/catcontent-agent.git
cd catcontent-agent
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file:

```env
GROQ_API_KEY=your_groq_api_key
PEXELS_API_KEY=your_pexels_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

### YouTube OAuth Setup

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable **YouTube Data API v3**
3. Create **OAuth 2.0 Client ID** (Desktop app)
4. Download `client_secret.json` to project root
5. Run `python agent.py generate --upload` — browser opens for OAuth consent
6. Token saved to `youtube_token.json` for future use

## Usage

```bash
# Generate and upload one video
python agent.py generate --upload --privacy public

# Generate without uploading (local preview)
python agent.py generate

# Generate a batch of 7 videos
python agent.py batch --count 7 --upload

# Upload an existing video
python agent.py upload output/short_20260311_203059

# Generate script only (no video)
python agent.py script

# Generate title ideas
python agent.py titles "cat sleeping habits"

# Pick a specific content format
python agent.py generate --format cat_myths --upload
```

## Automation

### GitHub Actions (Recommended — runs without your PC)

The workflow at `.github/workflows/daily-upload.yml` runs automatically:

- **8:00 AM PHT** (Manila time) — morning upload
- **6:00 PM PHT** — evening upload
- **Manual trigger** — workflow_dispatch button in GitHub Actions

Required GitHub Secrets:

| Secret | Description |
|--------|-------------|
| `GROQ_API_KEY` | Groq API key for LLM |
| `PEXELS_API_KEY` | Pexels API key for footage |
| `CLIENT_SECRET_JSON` | Full contents of `client_secret.json` |
| `YOUTUBE_TOKEN_JSON` | Full contents of `youtube_token.json` |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID |

The workflow automatically commits updated history files (`used_footage.json`, `used_scripts.json`, `youtube_token.json`) back to the repo after each run.

### Windows Task Scheduler (Local)

```bash
# Uses daily_upload.bat — logs to logs/daily.log
schtasks /create /tn "CatVideo_8AM" /tr "C:\path\to\daily_upload.bat" /sc daily /st 08:00
schtasks /create /tn "CatVideo_6PM" /tr "C:\path\to\daily_upload.bat" /sc daily /st 18:00
```

## Project Structure

```
catcontent-agent/
├── .github/workflows/
│   └── daily-upload.yml    # Automated daily upload (8AM + 6PM PHT)
├── music/                  # Background music tracks (7 files)
│   ├── chill-bg.mp3
│   ├── funny-bg.mp3
│   ├── upbeat-bg.mp3
│   ├── upbeat-fun.mp3
│   ├── ambient-soft.mp3
│   ├── dreamy-pad.mp3
│   └── warm-drone.mp3
├── output/                 # Generated videos (gitignored)
├── agent.py                # Main CLI
├── config.py               # Configuration & API keys
├── script_generator.py     # LLM script generation
├── footage_finder.py       # Pexels footage search & download
├── video_assembler.py      # FFmpeg video assembly
├── thumbnail_generator.py  # Thumbnail generation
├── youtube_uploader.py     # YouTube upload via API
├── voice_generator.py      # Edge TTS (optional)
├── notifier.py             # Telegram notifications
├── capture_assets.py       # Channel branding capture (Playwright)
├── daily_upload.bat         # Windows Task Scheduler script
├── used_footage.json       # Footage history (anti-repeat)
├── used_scripts.json       # Script history (anti-repeat)
├── requirements.txt
└── .env                    # API keys (gitignored)
```

## Tech Stack

| Component | Service | Cost |
|-----------|---------|------|
| LLM | [Groq](https://groq.com/) (Llama 3.3 70B) | Free |
| Stock Footage | [Pexels API](https://www.pexels.com/api/) | Free |
| Video Assembly | FFmpeg | Free |
| Text-to-Speech | Edge TTS (optional) | Free |
| YouTube Upload | YouTube Data API v3 | Free |
| Notifications | Telegram Bot API | Free |
| Automation | GitHub Actions | Free |
| **Total** | | **$0/month** |

## Roadmap

- **Phase 1** (Current) — Free stock footage + text overlays + music
- **Phase 2** — AI-generated clips via [Kling AI](https://klingai.com/) ($20-30/mo) for unique footage
- **Phase 3** — Full automation with Kling API + analytics-driven content optimization

## License

Private project.
