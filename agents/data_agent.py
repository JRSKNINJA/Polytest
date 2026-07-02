from datetime import datetime

from config import BACKTEST_YEARS, SYMBOL
from data.binance_client import create_client, fetch_current_price, fetch_ohlcv
from .base_agent import BaseAgent


class DataAgent(BaseAgent):
    def __init__(self):
        super().__init__("DataAgent")

    async def run(self) -> dict:
        self.log("Fetching BTC historical data from Binance...")
        client = await create_client()
        try:
            daily = await fetch_ohlcv(client, "1d", BACKTEST_YEARS)
            current_price = await fetch_current_price(client)
        finally:
            await client.close_connection()
        self.log(f"Fetched {len(daily)} daily candles. Price: ${current_price:,.2f}")
        return {
            "daily": daily.to_dict(),
            "current_price": current_price,
            "symbol": SYMBOL,
            "fetched_at": datetime.now().isoformat(),
        }
