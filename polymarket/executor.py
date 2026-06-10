from .client import PolymarketClient
from .market_finder import MarketFinder


class Executor:
    def __init__(self):
        self.client = PolymarketClient()
        self.finder = MarketFinder()

    def execute_signal(self, signal: int, current_price: float, amount_usdc: float) -> dict:
        market = self.finder.select_best_market(signal, current_price)
        if not market:
            return {"status": "no_market"}

        tokens = market.get("tokens", [])
        if not tokens:
            return {"status": "error", "reason": "no tokens"}

        token_id = tokens[0]["token_id"]
        try:
            orderbook = self.client.get_orderbook(token_id)
            asks = orderbook.get("asks", [])
            price = float(asks[0]["price"]) if asks else 0.5
            size = round(amount_usdc / price, 2)
            order = self.client.place_order(token_id, price, size, "BUY")
            return {"status": "executed", "order": order, "market": market.get("question")}
        except Exception as e:
            return {"status": "error", "reason": str(e)}
