import os
import time
import requests
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask

app = Flask(__name__)

# Environment variables se read karein (security ke liye hardcode na karein)
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8111921192:AAGaMpBB4tFkHUeadZE5Oip2tE9Fi8D1V2I")
CHAT_ID = os.environ.get("CHAT_ID", "5927722006")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyAAAfPtWSZokNwrF9A_mlbqU1o4uJR_X8A")
VIDEO_ID = os.environ.get("VIDEO_ID", "Z4hVGCWH1Kc")

# Safety check
if not BOT_TOKEN or not CHAT_ID or not GOOGLE_API_KEY:
    print("⚠ Missing TELEGRAM_BOT_TOKEN, CHAT_ID, or GOOGLE_API_KEY environment variables.")

YOUTUBE_STATS_URL = "https://www.googleapis.com/youtube/v3/videos"

def get_view_count(video_id: str) -> int | None:
    """YouTube API se view count fetch kare."""
    params = {
        "part": "statistics",
        "id": video_id,
        "key": GOOGLE_API_KEY
    }
    try:
        resp = requests.get(YOUTUBE_STATS_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        if not items:
            print("No items returned from YouTube API:", data)
            return None
        stats = items[0].get("statistics", {})
        return int(stats.get("viewCount", 0))
    except Exception as e:
        print("Error fetching YouTube stats:", e)
        return None

def send_telegram(text: str):
    """Telegram bot par message send kare."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        r = requests.post(url, data=payload, timeout=10)
        if r.status_code != 200:
            print("Telegram send failed:", r.status_code, r.text)
    except Exception as e:
        print("Exception sending Telegram:", e)

def sleep_until_next_5min():
    """
    Exact agle 5-minute mark tak wait kare.
    Example: 12:03:22 -> 12:05:00,  12:10:00 -> 12:15:00
    """
    now = datetime.utcnow()
    # Current minute ko nearest lower multiple of 5 pe leke jao
    minute = (now.minute // 5) * 5
    next_minute = now.replace(minute=minute, second=0, microsecond=0) + timedelta(minutes=5)
    seconds_to_sleep = (next_minute - now).total_seconds()
    print(f"Sleeping for {seconds_to_sleep:.1f}s until next interval {next_minute} (UTC)")
    time.sleep(seconds_to_sleep)

def job_loop():
    """Main scheduler loop."""
    print("Scheduler thread started.")
    while True:
        try:
            sleep_until_next_5min()
            now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            view_count = get_view_count(VIDEO_ID)
            if view_count is None:
                text = f"[{now}] Unable to fetch view count for video {VIDEO_ID}."
            else:
                text = f"[{now}] Video <b>{VIDEO_ID}</b> views: <b>{view_count:,}</b>"
            print("Sending:", text)
            send_telegram(text)
        except Exception as e:
            print("Unexpected error in scheduler:", e)
            time.sleep(30)

def start_scheduler():
    """Background scheduler thread start kare."""
    t = Thread(target=job_loop)
    t.daemon = True
    t.start()

@app.route("/")
def index():
    return "YouTube → Telegram notifier running."

start_scheduler()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
