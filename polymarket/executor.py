from .client import PolymarketClient
from .market_finder import MarketFinder


def select_token(market: dict, direction: str) -> str:
    """Pick the outcome token matching the trade direction (YES or NO)."""
    tokens = market.get("tokens", [])
    for token in tokens:
        if str(token.get("outcome", "")).strip().lower() == direction.lower():
            return token.get("token_id", "")
    # Fallback: Polymarket lists the YES token first, NO second
    idx = 0 if direction.upper() == "YES" else 1
    if len(tokens) > idx:
        return tokens[idx].get("token_id", "")
    return ""


class Executor:
    """Single implementation of live order placement on the Polymarket CLOB."""

    def __init__(self, client: PolymarketClient | None = None):
        self.client = client or PolymarketClient()
        self.finder = MarketFinder(self.client)

    def execute(self, market: dict, direction: str, amount_usdc: float) -> dict:
        token_id = select_token(market, direction)
        if not token_id:
            return {"status": "error", "error": f"no {direction} token on market"}
        try:
            orderbook = self.client.get_orderbook(token_id)
            asks = orderbook.get("asks", [])
            # Best ask = lowest price, regardless of the API's sort order
            price = min((float(a["price"]) for a in asks), default=0.5)
            size = round(amount_usdc / price, 2)
            order = self.client.place_order(token_id, price, size, "BUY")
            order_id = (
                order.get("orderID", "") if isinstance(order, dict)
                else getattr(order, "orderID", "")
            )
            return {"status": "executed", "order_id": order_id, "price": price, "size": size}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def execute_signal(self, signal: int, current_price: float, amount_usdc: float) -> dict:
        market = self.finder.select_best_market(signal, current_price)
        if not market:
            return {"status": "no_market"}
        result = self.execute(market, "YES" if signal > 0 else "NO", amount_usdc)
        result["market"] = market.get("question")
        return result
