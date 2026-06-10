import asyncio
from datetime import datetime

import aiohttp

from .base_agent import BaseAgent


class MacroAgent(BaseAgent):
    FEAR_GREED_URL = "https://api.alternative.me/fng/?limit=1&format=json"
    BINANCE_FUNDING_URL = "https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT"
    BINANCE_OI_URL = "https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT"

    def __init__(self):
        super().__init__("MacroAgent")

    async def _fetch_fear_greed(self, session: aiohttp.ClientSession) -> dict:
        try:
            async with session.get(self.FEAR_GREED_URL, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json(content_type=None)
                entry = data["data"][0]
                return {
                    "value": int(entry["value"]),
                    "label": entry["value_classification"],
                }
        except Exception as e:
            self.log(f"Fear & Greed fetch failed: {e}")
            return {"value": 50, "label": "Neutral"}

    async def _fetch_funding_rate(self, session: aiohttp.ClientSession) -> float:
        try:
            async with session.get(self.BINANCE_FUNDING_URL, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json(content_type=None)
                return float(data.get("lastFundingRate", 0))
        except Exception as e:
            self.log(f"Funding rate fetch failed: {e}")
            return 0.0

    async def _fetch_open_interest(self, session: aiohttp.ClientSession) -> float:
        try:
            async with session.get(self.BINANCE_OI_URL, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json(content_type=None)
                return float(data.get("openInterest", 0))
        except Exception as e:
            self.log(f"Open interest fetch failed: {e}")
            return 0.0

    async def run(self) -> dict:
        self.log("Fetching macro data (Fear&Greed, funding rate, OI)...")
        async with aiohttp.ClientSession() as session:
            fg, funding, oi = await asyncio.gather(
                self._fetch_fear_greed(session),
                self._fetch_funding_rate(session),
                self._fetch_open_interest(session),
            )

        fg_value = fg["value"]
        # Normalize: F&G > 60 = greed = potential reversal signal (-1), < 40 = fear = opportunity (+1)
        fg_signal = 1 if fg_value < 40 else (-1 if fg_value > 60 else 0)
        # Funding rate: very positive = overleveraged longs = bearish (-1), very negative = bearish bets = bullish (+1)
        funding_signal = -1 if funding > 0.0005 else (1 if funding < -0.0001 else 0)

        self.log(f"F&G={fg_value} ({fg['label']}), funding={funding:.6f}, OI={oi:,.0f}")
        return {
            "fear_greed": fg,
            "fear_greed_signal": fg_signal,
            "funding_rate": funding,
            "funding_signal": funding_signal,
            "open_interest": oi,
            "fetched_at": datetime.now().isoformat(),
        }
