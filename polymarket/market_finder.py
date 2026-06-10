import re

from .client import PolymarketClient

BTC_KEYWORDS = ["bitcoin", "btc"]
PRICE_KEYWORDS = ["price", "above", "below", "reach", "hit", "exceed", "cross", "$"]


class MarketFinder:
    def __init__(self):
        self.client = PolymarketClient()

    def find_btc_markets(self) -> list[dict]:
        btc_markets = []
        next_cursor = "MA=="

        while True:
            try:
                response = self.client.get_markets(next_cursor=next_cursor)
                markets = response.get("data", [])

                for market in markets:
                    q = market.get("question", "").lower()
                    has_btc = any(kw in q for kw in BTC_KEYWORDS)
                    has_price = any(kw in q for kw in PRICE_KEYWORDS)
                    if has_btc and has_price and market.get("active", False):
                        btc_markets.append(market)

                next_cursor = response.get("next_cursor")
                if not next_cursor or next_cursor in ("LTE=", ""):
                    break
            except Exception:
                break

        return btc_markets

    def score_market(self, market: dict, signal: int, current_price: float) -> float:
        q = market.get("question", "")
        match = re.search(r"\$([\d,]+)([kK]?)", q)
        if not match:
            return 0.0

        try:
            raw = float(match.group(1).replace(",", ""))
            multiplier = 1000 if match.group(2).lower() == "k" else 1
            target = raw * multiplier
        except Exception:
            return 0.0

        if signal > 0 and target > current_price:
            return 0.85
        if signal < 0 and target < current_price:
            return 0.85
        if signal > 0 and target > current_price * 0.95:
            return 0.60
        return 0.20

    def select_best_market(self, signal: int, current_price: float) -> dict | None:
        markets = self.find_btc_markets()
        if not markets:
            return None
        scored = sorted(
            ((self.score_market(m, signal, current_price), m) for m in markets),
            key=lambda x: x[0],
            reverse=True,
        )
        return scored[0][1] if scored else None
