from datetime import datetime, timedelta

import pandas as pd
from binance import AsyncClient

from config import BINANCE_API_KEY, BINANCE_API_SECRET, SYMBOL


async def fetch_ohlcv(interval: str = "1d", lookback_years: int = 5) -> pd.DataFrame:
    client = await AsyncClient.create(BINANCE_API_KEY, BINANCE_API_SECRET)
    start = datetime.now() - timedelta(days=365 * lookback_years)
    klines = await client.get_historical_klines(SYMBOL, interval, str(start))
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


async def fetch_current_price() -> float:
    client = await AsyncClient.create(BINANCE_API_KEY, BINANCE_API_SECRET)
    ticker = await client.get_symbol_ticker(symbol=SYMBOL)
    await client.close_connection()
    return float(ticker["price"])
