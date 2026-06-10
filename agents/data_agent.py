import asyncio
from datetime import datetime, timedelta

import pandas as pd
from binance import AsyncClient

from config import BINANCE_API_KEY, BINANCE_API_SECRET, SYMBOL
from .base_agent import BaseAgent


class DataAgent(BaseAgent):
    def __init__(self):
        super().__init__("DataAgent")

    async def fetch_historical_data(self, interval: str = "1d", lookback_years: int = 5) -> pd.DataFrame:
        client = await AsyncClient.create(BINANCE_API_KEY, BINANCE_API_SECRET)
        start = datetime.now() - timedelta(days=365 * lookback_years)
        klines = await client.get_historical_klines(
            SYMBOL, interval, str(start), str(datetime.now())
        )
        await client.close_connection()

        df = pd.DataFrame(
            klines,
            columns=[
                "timestamp", "open", "high", "low", "close", "volume",
                "close_time", "quote_volume", "trades", "taker_buy_base",
                "taker_buy_quote", "ignore",
            ],
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        return df

    async def fetch_realtime_price(self) -> float:
        client = await AsyncClient.create(BINANCE_API_KEY, BINANCE_API_SECRET)
        ticker = await client.get_symbol_ticker(symbol=SYMBOL)
        await client.close_connection()
        return float(ticker["price"])

    async def run(self) -> dict:
        self.log("Fetching BTC historical data from Binance...")
        daily = await self.fetch_historical_data("1d", 5)
        hourly = await self.fetch_historical_data("1h", 1)
        current_price = await self.fetch_realtime_price()
        self.log(f"Fetched {len(daily)} daily + {len(hourly)} hourly candles. Price: ${current_price:,.2f}")
        return {
            "daily": daily.to_dict(),
            "hourly": hourly.to_dict(),
            "current_price": current_price,
            "symbol": SYMBOL,
            "fetched_at": datetime.now().isoformat(),
        }
