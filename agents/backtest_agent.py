import pandas as pd

from backtest.engine import run_backtest
from .base_agent import BaseAgent


class BacktestAgent(BaseAgent):
    def __init__(self, market_data: dict, signals: dict):
        super().__init__("BacktestAgent")
        self.data = market_data
        self.signals = signals

    async def run(self) -> dict:
        self.log("Running 5-year backtest...")
        df = pd.DataFrame(self.data.get("daily", {}))
        sig_df = pd.DataFrame(self.signals.get("signals", {}))

        if df.empty or sig_df.empty:
            return {"error": "Missing data for backtest"}

        result = run_backtest(df, sig_df)
        self.log(
            f"Return={result['total_return_pct']:.1f}%, "
            f"Sharpe={result['sharpe_ratio']:.2f}, "
            f"MaxDD={result['max_drawdown_pct']:.1f}%, "
            f"WinRate={result['win_rate_pct']:.1f}%"
        )
        return result
