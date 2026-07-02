from config import MAX_DRAWDOWN_LIMIT, MAX_POSITION_SIZE, MIN_SHARPE_RATIO
from risk.manager import RiskManager
from .base_agent import BaseAgent


class RiskAgent(BaseAgent):
    def __init__(self, backtest_results: dict):
        super().__init__("RiskAgent")
        self.backtest = backtest_results

    async def run(self) -> dict:
        self.log("Assessing risk...")
        bt = self.backtest
        result = RiskManager().evaluate(bt)
        result["metrics"] = {
            "sharpe_ratio": bt.get("sharpe_ratio", 0),
            "max_drawdown_pct": bt.get("max_drawdown_pct", -100),
            "win_rate_pct": bt.get("win_rate_pct", 0),
            "total_return_pct": bt.get("total_return_pct", 0),
        }
        result["limits"] = {
            "max_position_size_pct": MAX_POSITION_SIZE * 100,
            "max_drawdown_pct": MAX_DRAWDOWN_LIMIT * 100,
            "min_sharpe": MIN_SHARPE_RATIO,
        }
        status = "APPROVED" if result["approved"] else "REJECTED"
        self.log(
            f"Risk {status}: score={result['risk_score']}, "
            f"position_size={result['position_size']:.2%}"
        )
        for issue in result["issues"]:
            self.log(f"  WARNING: {issue}")
        return result
