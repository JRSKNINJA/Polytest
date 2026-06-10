import os
from datetime import datetime

import aiohttp

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from .base_agent import BaseAgent


class Notifier(BaseAgent):
    BASE_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self):
        super().__init__("Notifier")

    async def _send(self, text: str) -> bool:
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            self.log("Telegram not configured — skipping notification")
            return False
        url = self.BASE_URL.format(token=TELEGRAM_BOT_TOKEN)
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown",
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as r:
                    ok = r.status == 200
                    if not ok:
                        self.log(f"Telegram send failed: HTTP {r.status}")
                    return ok
        except Exception as e:
            self.log(f"Telegram error: {e}")
            return False

    async def send_trade_alert(self, execution: dict, all_results: dict) -> None:
        status = execution.get("status", "unknown")
        btc_price = all_results.get("data", {}).get("current_price", 0)
        signal = all_results.get("signals", {}).get("current_position", 0)
        risk_score = all_results.get("orchestrator_review", {}).get("risk_score", 0)
        fg = all_results.get("macro", {}).get("fear_greed", {})

        direction_emoji = {"1": "🟢", "-1": "🔴", "0": "⚪"}.get(str(signal), "⚪")
        status_emoji = {"paper_trade": "📄", "executed": "✅", "blocked": "🚫", "no_trade": "⏸", "error": "❌"}.get(status, "❓")

        msg = (
            f"{status_emoji} *GCM Bot — Cycle Complete*\n\n"
            f"₿ BTC: `${btc_price:,.0f}`\n"
            f"{direction_emoji} Signal: `{'BUY' if signal > 0 else 'SELL' if signal < 0 else 'FLAT'}`\n"
            f"⚠️ Risk: `{risk_score}/100`\n"
            f"😱 Fear & Greed: `{fg.get('value', 'N/A')} — {fg.get('label', 'N/A')}`\n"
            f"📊 Status: `{status}`\n"
        )

        if status in ("paper_trade", "executed"):
            msg += (
                f"💵 Amount: `${execution.get('amount_usdc', 0):,.2f} USDC`\n"
                f"🏪 Market: _{execution.get('market', 'N/A')[:80]}_\n"
            )
        elif status == "blocked":
            msg += f"🔒 Reason: `{execution.get('reason', 'N/A')}`\n"

        msg += f"\n_⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}_"
        await self._send(msg)

    async def send_risk_alert(self, risk_score: int, issues: list) -> None:
        issue_lines = "\n".join(f"• {i}" for i in issues)
        msg = (
            f"🚨 *GCM Bot — Risk Alert*\n\n"
            f"Score: `{risk_score}/100`\n\n"
            f"Issues:\n{issue_lines}\n\n"
            f"_Trading halted until conditions improve_"
        )
        await self._send(msg)

    async def run(self) -> dict:
        return {}
