from config import MAX_DRAWDOWN_LIMIT, MAX_POSITION_SIZE, MIN_SHARPE_RATIO


class RiskManager:
    MIN_WIN_RATE = 45.0

    def evaluate(self, backtest: dict) -> dict:
        issues = []
        risk_score = 0
        size = MAX_POSITION_SIZE

        sharpe = backtest.get("sharpe_ratio", 0)
        max_dd = backtest.get("max_drawdown_pct", -100)
        win_rate = backtest.get("win_rate_pct", 0)
        ret = backtest.get("total_return_pct", 0)

        if sharpe < MIN_SHARPE_RATIO:
            issues.append(f"Sharpe {sharpe:.2f} below minimum {MIN_SHARPE_RATIO}")
            risk_score += 30
            size *= 0.5

        if max_dd < MAX_DRAWDOWN_LIMIT * 100:
            issues.append(f"Max drawdown {max_dd:.1f}% breaches {MAX_DRAWDOWN_LIMIT * 100:.0f}% limit")
            risk_score += 40
            size *= 0.25

        if win_rate < self.MIN_WIN_RATE:
            issues.append(f"Win rate {win_rate:.1f}% below {self.MIN_WIN_RATE}%")
            risk_score += 20

        if ret < 0:
            issues.append(f"Negative return {ret:.1f}%")
            risk_score += 30

        risk_score = min(risk_score, 100)
        return {
            "approved": risk_score < 50 and len(issues) < 2,
            "risk_score": risk_score,
            "position_size": round(size, 4),
            "issues": issues,
        }
