"""Run after setting TELEGRAM_CHAT_ID in .env to verify the bot works."""
import asyncio
import os

from dotenv import load_dotenv

load_dotenv()


async def main():
    import aiohttp

    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id or chat_id == "REPLACE_WITH_YOUR_CHAT_ID":
        print("ERROR: Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env first")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": (
            "✅ *GCM Bot — Connected*\n\n"
            "Telegram alerts are working\\. "
            "You'll receive a message after every trading cycle\\."
        ),
        "parse_mode": "MarkdownV2",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as r:
            body = await r.json()
            if r.status == 200:
                print("Test message sent successfully.")
            else:
                print(f"Failed: HTTP {r.status}")
                print(body)


asyncio.run(main())
