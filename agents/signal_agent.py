import numpy as np
import pandas as pd

from .base_agent import BaseAgent


class SignalAgent(BaseAgent):
    def __init__(self, market_data: dict, macro_data: dict | None = None):
        super().__init__("SignalAgent")
        self.data = market_data
        self.macro = macro_data or {}

    @staticmethod
    def _rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        delta = prices.diff()
        gain = delta.where(delta > 0, 0.0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
        rs = gain / loss.replace(0, float("nan"))
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _macd(prices: pd.Series, fast=12, slow=26, signal=9):
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        sig = macd.ewm(span=signal).mean()
        return macd, sig, macd - sig

    @staticmethod
    def _bollinger(prices: pd.Series, period=20, n_std=2):
        sma = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        return sma + n_std * std, sma, sma - n_std * std

    def _generate(self, df: pd.DataFrame) -> pd.DataFrame:
        p = df["close"]
        sig = pd.DataFrame(index=df.index)

        rsi = self._rsi(p)
        sig["rsi"] = rsi
        sig["rsi_signal"] = np.where(rsi < 30, 1, np.where(rsi > 70, -1, 0))

        macd, macd_sig, hist = self._macd(p)
        sig["macd_hist"] = hist
        sig["macd_signal"] = np.where(hist > 0, 1, -1)

        upper, mid, lower = self._bollinger(p)
        sig["bb_signal"] = np.where(p < lower, 1, np.where(p > upper, -1, 0))

        sma20 = p.rolling(20).mean()
        sma50 = p.rolling(50).mean()
        sma200 = p.rolling(200).mean()
        sig["trend"] = np.where(sma20 > sma50, 1, -1)
        sig["bull_market"] = (p > sma200).astype(int)

        vol_ma = df["volume"].rolling(20).mean()
        sig["volume_surge"] = (df["volume"] > vol_ma * 1.5).astype(int)

        sig["composite"] = (
            sig["rsi_signal"] * 0.30
            + sig["macd_signal"] * 0.30
            + sig["bb_signal"] * 0.20
            + sig["trend"] * 0.20
        )
        sig["final_signal"] = np.where(
            sig["composite"] > 0.3, 1, np.where(sig["composite"] < -0.3, -1, 0)
        )
        return sig

    async def run(self) -> dict:
        self.log("Generating trading signals...")
        df = pd.DataFrame(self.data.get("daily", {}))
        if df.empty:
            return {"error": "No market data"}

        signals = self._generate(df)

        macro_boost = (
            self.macro.get("fear_greed_signal", 0) * 0.15
            + self.macro.get("funding_signal", 0) * 0.10
        )
        # Adjust composite with macro signals
        signals["composite"] = signals["composite"] + macro_boost
        signals["final_signal"] = np.where(
            signals["composite"] > 0.3, 1, np.where(signals["composite"] < -0.3, -1, 0)
        )

        latest = signals.iloc[-1]
        recent = signals.tail(30)

        self.log(
            f"Signal={int(latest['final_signal'])}, RSI={latest['rsi']:.1f}, "
            f"Trend={'bullish' if latest['trend'] > 0 else 'bearish'}, "
            f"MacroBoost={macro_boost:+.2f}"
        )
        return {
            "signals": signals.tail(100).to_dict(),
            "latest_signal": {k: float(v) for k, v in latest.items()},
            "current_position": int(latest["final_signal"]),
            "rsi": float(latest["rsi"]),
            "trend": "bullish" if latest["trend"] > 0 else "bearish",
            "summary": {
                "bullish_days": int((recent["final_signal"] == 1).sum()),
                "bearish_days": int((recent["final_signal"] == -1).sum()),
                "neutral_days": int((recent["final_signal"] == 0).sum()),
                "avg_composite": float(recent["composite"].mean()),
            },
            "macro": {
                "fear_greed": self.macro.get("fear_greed", {}),
                "funding_rate": self.macro.get("funding_rate", 0),
                "fear_greed_signal": self.macro.get("fear_greed_signal", 0),
                "funding_signal": self.macro.get("funding_signal", 0),
            },
        }
