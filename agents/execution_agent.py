from datetime import datetime

from config import PAPER_TRADING
from polymarket.client import PolymarketClient
from polymarket.market_finder import MarketFinder
from .base_agent import BaseAgent


class ExecutionAgent(BaseAgent):
    def __init__(self, analysis_results: dict):
        super().__init__("ExecutionAgent")
        self.results = analysis_results
        self.client = PolymarketClient()
        self.finder = MarketFinder()

    async def run(self) -> dict:
        self.log(f"Starting execution (paper_trading={PAPER_TRADING})...")

        signal = self.results.get("signals", {}).get("current_position", 0)
        current_price = self.results.get("data", {}).get("current_price", 0)
        risk = self.results.get("risk", {})
        review = self.results.get("review", {})

        if not risk.get("approved", False):
            self.log("Blocked: risk not approved")
            return {"status": "blocked", "reason": "risk not approved"}

        if not review.get("approved", False):
            self.log("Blocked: review not approved")
            return {"status": "blocked", "reason": "review not approved"}

        if signal == 0:
            self.log("No signal — staying flat")
            return {"status": "no_trade", "reason": "neutral signal"}

        market = self.finder.select_best_market(signal, current_price)
        if not market:
            self.log("No suitable Polymarket found")
            return {"status": "no_market", "reason": "no suitable BTC market"}

        balance = self._get_balance()
        if balance < 10:
            self.log(f"Insufficient balance: ${balance:.2f}")
            return {"status": "insufficient_funds", "balance": balance}

        position_size = risk.get("position_size", 0.05)
        amount = min(balance * position_size, balance * 0.10)

        trade = {
            "status": "paper_trade" if PAPER_TRADING else "live_trade",
            "signal": signal,
            "direction": "YES" if signal > 0 else "NO",
            "market": market.get("question", "Unknown"),
            "condition_id": market.get("condition_id", ""),
            "amount_usdc": round(amount, 2),
            "btc_price": current_price,
            "timestamp": datetime.now().isoformat(),
        }

        if not PAPER_TRADING:
            trade = self._execute_live(trade, market, amount)

        self.log(
            f"Trade: {trade['direction']} ${trade['amount_usdc']} on '{trade['market'][:60]}'"
        )
        return trade

    def _get_balance(self) -> float:
        try:
            data = self.client.get_balance()
            return float(data.get("balance", 0))
        except Exception as e:
            self.log(f"Balance fetch failed: {e}. Using 0.")
            return 0.0

    def _execute_live(self, trade: dict, market: dict, amount: float) -> dict:
        try:
            tokens = market.get("tokens", [])
            token_id = tokens[0].get("token_id", "") if tokens else ""
            side = "BUY" if trade["direction"] == "YES" else "BUY"  # buy NO token
            if not token_id:
                trade["status"] = "error"
                trade["error"] = "No token_id found"
                return trade

            orderbook = self.client.get_orderbook(token_id)
            best_ask = float(orderbook.get("asks", [{"price": 0.5}])[0].get("price", 0.5))
            size = round(amount / best_ask, 2)

            result = self.client.place_order(token_id, best_ask, size, side)
            trade["order_id"] = result.get("orderID", "")
            trade["status"] = "executed"
        except Exception as e:
            trade["status"] = "error"
            trade["error"] = str(e)
        return trade
