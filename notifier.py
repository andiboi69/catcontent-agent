"""
Telegram Notifier — Sends status updates to your phone.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"


def send_notification(message):
    """Send a Telegram message."""
    if not BOT_TOKEN or not CHAT_ID:
        print("  Telegram not configured, skipping notification")
        return False

    try:
        resp = requests.post(API_URL, json={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
        }, timeout=10)
        return resp.ok
    except Exception as e:
        print(f"  Telegram notification failed: {e}")
        return False


def notify_upload_success(title, url):
    """Notify that a video was uploaded successfully."""
    msg = (
        f"✅ <b>Video Uploaded!</b>\n\n"
        f"📹 <b>{title}</b>\n"
        f"🔗 {url}\n\n"
        f"🐱 Purrfect Facts Agent"
    )
    return send_notification(msg)


def notify_upload_failed(title, error):
    """Notify that a video upload failed."""
    msg = (
        f"❌ <b>Upload Failed</b>\n\n"
        f"📹 <b>{title}</b>\n"
        f"⚠️ {error}\n\n"
        f"🐱 Purrfect Facts Agent"
    )
    return send_notification(msg)


def notify_generation_failed(error):
    """Notify that video generation failed."""
    msg = (
        f"❌ <b>Generation Failed</b>\n\n"
        f"⚠️ {error}\n\n"
        f"🐱 Purrfect Facts Agent"
    )
    return send_notification(msg)
