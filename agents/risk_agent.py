from config import MAX_DRAWDOWN_LIMIT, MAX_POSITION_SIZE, MIN_SHARPE_RATIO
from .base_agent import BaseAgent


class RiskAgent(BaseAgent):
    MIN_WIN_RATE = 45.0

    def __init__(self, backtest_results: dict):
        super().__init__("RiskAgent")
        self.backtest = backtest_results

    def assess(self) -> dict:
        bt = self.backtest
        issues = []
        risk_score = 0
        position_size = MAX_POSITION_SIZE

        sharpe = bt.get("sharpe_ratio", 0)
        max_dd = bt.get("max_drawdown_pct", -100)
        win_rate = bt.get("win_rate_pct", 0)
        total_ret = bt.get("total_return_pct", 0)

        if sharpe < MIN_SHARPE_RATIO:
            issues.append(f"Low Sharpe: {sharpe:.2f} (min {MIN_SHARPE_RATIO})")
            risk_score += 30
            position_size *= 0.5

        if max_dd < MAX_DRAWDOWN_LIMIT * 100:
            issues.append(f"Excessive drawdown: {max_dd:.1f}%")
            risk_score += 40
            position_size *= 0.25

        if win_rate < self.MIN_WIN_RATE:
            issues.append(f"Low win rate: {win_rate:.1f}%")
            risk_score += 20

        if total_ret < 0:
            issues.append(f"Negative return: {total_ret:.1f}%")
            risk_score += 30

        risk_score = min(risk_score, 100)
        approved = risk_score < 50 and len(issues) < 2

        return {
            "approved": approved,
            "risk_score": risk_score,
            "position_size": round(position_size, 4),
            "issues": issues,
            "metrics": {
                "sharpe_ratio": sharpe,
                "max_drawdown_pct": max_dd,
                "win_rate_pct": win_rate,
                "total_return_pct": total_ret,
            },
            "limits": {
                "max_position_size_pct": MAX_POSITION_SIZE * 100,
                "max_drawdown_pct": MAX_DRAWDOWN_LIMIT * 100,
                "min_sharpe": MIN_SHARPE_RATIO,
            },
        }

    async def run(self) -> dict:
        self.log("Assessing risk...")
        result = self.assess()
        status = "APPROVED" if result["approved"] else "REJECTED"
        self.log(
            f"Risk {status}: score={result['risk_score']}, "
            f"position_size={result['position_size']:.2%}"
        )
        for issue in result["issues"]:
            self.log(f"  WARNING: {issue}")
        return result
