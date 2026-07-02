from datetime import datetime, timedelta

import pandas as pd
from binance import AsyncClient

from config import BINANCE_API_KEY, BINANCE_API_SECRET, SYMBOL

KLINE_COLUMNS = [
    "timestamp", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades", "taker_buy_base",
    "taker_buy_quote", "ignore",
]


async def create_client() -> AsyncClient:
    return await AsyncClient.create(BINANCE_API_KEY, BINANCE_API_SECRET)


async def fetch_ohlcv(client: AsyncClient, interval: str = "1d", lookback_years: int = 5) -> pd.DataFrame:
    start = datetime.now() - timedelta(days=365 * lookback_years)
    klines = await client.get_historical_klines(
        SYMBOL, interval, str(start), str(datetime.now())
    )
    df = pd.DataFrame(klines, columns=KLINE_COLUMNS)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    return df


async def fetch_current_price(client: AsyncClient) -> float:
    ticker = await client.get_symbol_ticker(symbol=SYMBOL)
    return float(ticker["price"])
