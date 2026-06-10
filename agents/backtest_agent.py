import numpy as np
import pandas as pd

from .base_agent import BaseAgent


class BacktestAgent(BaseAgent):
    def __init__(self, market_data: dict, signals: dict):
        super().__init__("BacktestAgent")
        self.data = market_data
        self.signals = signals

    def _run_backtest(
        self,
        df: pd.DataFrame,
        signal_df: pd.DataFrame,
        initial_capital: float = 10_000,
        position_size: float = 0.10,
    ) -> dict:
        port = pd.DataFrame(index=df.index)
        port["close"] = df["close"]
        port["signal"] = signal_df["final_signal"].reindex(df.index).fillna(0)
        port["position"] = port["signal"].shift(1).fillna(0)
        port["returns"] = df["close"].pct_change()
        port["strat_returns"] = port["position"] * port["returns"] * position_size

        port["cum_market"] = (1 + port["returns"]).cumprod()
        port["cum_strategy"] = (1 + port["strat_returns"]).cumprod()
        port["equity"] = initial_capital * port["cum_strategy"]

        total_ret = (port["equity"].iloc[-1] / initial_capital - 1) * 100
        years = max((port.index[-1] - port.index[0]).days / 365, 1)
        annual_ret = ((1 + total_ret / 100) ** (1 / years) - 1) * 100

        daily = port["strat_returns"].dropna()
        sharpe = (daily.mean() / daily.std()) * np.sqrt(252) if daily.std() > 0 else 0.0

        roll_max = port["equity"].cummax()
        max_dd = ((port["equity"] - roll_max) / roll_max).min() * 100

        active = port["strat_returns"][port["position"] != 0]
        win_rate = (active > 0).mean() * 100 if len(active) > 0 else 0.0

        return {
            "initial_capital": initial_capital,
            "final_capital": float(port["equity"].iloc[-1]),
            "total_return_pct": float(total_ret),
            "annual_return_pct": float(annual_ret),
            "sharpe_ratio": float(sharpe),
            "max_drawdown_pct": float(max_dd),
            "win_rate_pct": float(win_rate),
            "total_trades": int((port["position"].diff() != 0).sum()),
            "buy_hold_return_pct": float((port["cum_market"].iloc[-1] - 1) * 100),
            "equity_curve": port["equity"].tail(100).to_dict(),
        }

    async def run(self) -> dict:
        self.log("Running 5-year backtest...")
        df = pd.DataFrame(self.data.get("daily", {}))
        sig_df = pd.DataFrame(self.signals.get("signals", {}))

        if df.empty or sig_df.empty:
            return {"error": "Missing data for backtest"}

        result = self._run_backtest(df, sig_df)
        self.log(
            f"Return={result['total_return_pct']:.1f}%, "
            f"Sharpe={result['sharpe_ratio']:.2f}, "
            f"MaxDD={result['max_drawdown_pct']:.1f}%, "
            f"WinRate={result['win_rate_pct']:.1f}%"
        )
        return result
