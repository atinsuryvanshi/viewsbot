import os
import time
import requests
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask

app = Flask(__name__)

# Read secrets from environment variables (do NOT hardcode)
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8111921192:AAGaMpBB4tFkHUeadZE5Oip2tE9Fi8D1V2I")
CHAT_ID = os.environ.get("CHAT_ID", "5927722006")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyAAAfPtWSZokNwrF9A_mlbqU1o4uJR_X8A")
VIDEO_ID = os.environ.get("VIDEO_ID", "M2lX9XESvDE")

# safety checks
if not BOT_TOKEN or not CHAT_ID or not GOOGLE_API_KEY:
    print("Warning: Missing TELEGRAM_BOT_TOKEN, CHAT_ID or GOOGLE_API_KEY environment variables.")

YOUTUBE_STATS_URL = "https://www.googleapis.com/youtube/v3/videos"

def get_view_count(video_id: str) -> int | None:
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
            print("No items returned from YouTube API. Response:", data)
            return None
        stats = items[0].get("statistics", {})
        view_count = int(stats.get("viewCount", 0))
        return view_count
    except Exception as e:
        print("Error fetching YouTube stats:", e)
        return None

def send_telegram(text: str):
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

def job_loop():
    """
    Main scheduler loop:
    - Send initial view count on startup
    - Check views every 5 seconds
    - Only send updates when views change
    - Show view gain and update time
    """
    print("Scheduler thread started.")
    previous_views = None
    
    # Send initial view count
    view_count = get_view_count(VIDEO_ID)
    if view_count is not None:
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        text = f"[{now}] Video <b>{VIDEO_ID}</b> initial views: <b>{view_count:,}</b>"
        print("Sending initial:", text)
        send_telegram(text)
        previous_views = view_count
    else:
        print("Failed to fetch initial view count")
    
    while True:
        try:
            time.sleep(5)  # Check every 5 seconds
            view_count = get_view_count(VIDEO_ID)
            if view_count is None:
                continue
                
            # Only send update if views have changed
            if previous_views is not None and view_count != previous_views:
                now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
                view_gain = view_count - previous_views
                text = f"[{now}] Video <b>{VIDEO_ID}</b> views: <b>{view_count:,}</b> (+{view_gain:,})"
                print("Sending update:", text)
                send_telegram(text)
                previous_views = view_count
                
        except Exception as e:
            print("Unexpected error in scheduler:", e)
            time.sleep(5)  # Wait before retrying

# start background thread for scheduler so Flask stays running
def start_scheduler():
    t = Thread(target=job_loop)
    t.daemon = True
    t.start()

@app.route("/")
def index():
    return "YouTube -> Telegram notifier running."

start_scheduler()

if __name__ == "__main__":
    # For local testing only
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
