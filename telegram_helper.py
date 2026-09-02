"""Shared Telegram sender — loads credentials from .env (never hardcoded)."""
import os
import requests

def _load_env():
    """Load .env from project root."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    env = {}
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    except FileNotFoundError:
        pass
    return env

def get_credentials():
    """Return (token, chat_id) from .env or environment variables."""
    env = _load_env()
    token = env.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = env.get("TELEGRAM_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID")
    return token, chat_id

def send_message(text, token=None, chat_id=None):
    """Send a text message to Telegram. Returns True on success."""
    if token is None or chat_id is None:
        token, chat_id = get_credentials()
    if not token or not chat_id:
        print("ERROR: No Telegram credentials found. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    chunks = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > 3500:
            chunks.append(current)
            current = ""
        current += line + "\n"
    if current:
        chunks.append(current)

    ok = True
    for chunk in chunks:
        resp = requests.post(url, json={
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }, timeout=15)
        if not resp.ok:
            ok = False
            print(f"Telegram error: {resp.text[:200]}")
    return ok

def send_photo(photo_path, caption="", token=None, chat_id=None):
    """Send a photo to Telegram. Returns True on success."""
    if token is None or chat_id is None:
        token, chat_id = get_credentials()
    if not token or not chat_id:
        print("ERROR: No Telegram credentials found.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    with open(photo_path, "rb") as f:
        resp = requests.post(url, data={
            "chat_id": chat_id,
            "caption": caption,
        }, files={"photo": f}, timeout=30)
    return resp.ok
