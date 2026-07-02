import asyncio
from datetime import datetime

import config
from polymarket.client import PolymarketClient
from polymarket.executor import Executor
from .base_agent import BaseAgent


class ExecutionAgent(BaseAgent):
    def __init__(self, analysis_results: dict):
        super().__init__("ExecutionAgent")
        self.results = analysis_results
        self.client = PolymarketClient()
        self.executor = Executor(self.client)

    async def run(self) -> dict:
        self.log(f"Starting execution (paper_trading={config.PAPER_TRADING})...")

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

        # The Polymarket client is synchronous — keep its network calls off
        # the event loop so the rest of the bot stays responsive.
        market = await asyncio.to_thread(
            self.executor.finder.select_best_market, signal, current_price
        )
        if not market:
            if not config.PAPER_TRADING:
                self.log("No suitable Polymarket found")
                return {"status": "no_market", "reason": "no suitable BTC market"}
            # Paper mode works without Polymarket credentials/reachability —
            # simulate a market so the strategy still gets exercised and logged.
            direction_word = "above" if signal > 0 else "below"
            market = {
                "question": f"[SIM] Will BTC be {direction_word} ${current_price:,.0f}?",
                "condition_id": "paper-sim",
            }
            self.log("No live market data — using simulated paper market")

        if config.PAPER_TRADING:
            balance = config.PAPER_BALANCE
        else:
            balance = await asyncio.to_thread(self._get_balance)
        if balance < 10:
            self.log(f"Insufficient balance: ${balance:.2f}")
            return {"status": "insufficient_funds", "balance": balance}

        position_size = risk.get("position_size", 0.05)
        amount = min(balance * position_size, balance * 0.10)
        direction = "YES" if signal > 0 else "NO"

        trade = {
            "status": "paper_trade",
            "signal": signal,
            "direction": direction,
            "market": market.get("question", "Unknown"),
            "condition_id": market.get("condition_id", ""),
            "amount_usdc": round(amount, 2),
            "btc_price": current_price,
            "timestamp": datetime.now().isoformat(),
        }

        if not config.PAPER_TRADING:
            result = await asyncio.to_thread(self.executor.execute, market, direction, amount)
            trade.update(result)

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
