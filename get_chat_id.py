"""
Run this once to find your Telegram chat ID.
Steps:
  1. Open Telegram and send any message to @MJAbtcscalperbot
  2. Run: python get_chat_id.py
  3. Copy the chat_id printed
  4. Paste it into .env as TELEGRAM_CHAT_ID=<value>
"""
import json
import os
import urllib.request

from dotenv import load_dotenv

load_dotenv()

token = os.getenv("TELEGRAM_BOT_TOKEN", "")
if not token:
    print("ERROR: TELEGRAM_BOT_TOKEN not set in .env")
    raise SystemExit(1)

url = f"https://api.telegram.org/bot{token}/getUpdates"
with urllib.request.urlopen(url) as r:
    data = json.loads(r.read())

updates = data.get("result", [])
if not updates:
    print("No messages found. Send any message to @MJAbtcscalperbot first, then re-run.")
    raise SystemExit(1)

seen = set()
for u in updates:
    msg = u.get("message") or u.get("channel_post") or {}
    chat = msg.get("chat", {})
    cid = chat.get("id")
    name = chat.get("title") or chat.get("username") or chat.get("first_name", "")
    if cid and cid not in seen:
        seen.add(cid)
        print(f"chat_id: {cid}  ({chat.get('type', '')} — {name})")

print("\nAdd the correct chat_id to your .env as TELEGRAM_CHAT_ID=<value>")
