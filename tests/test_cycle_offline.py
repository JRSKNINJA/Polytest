"""Offline end-to-end test: runs a full trading cycle with synthetic market
data (no network, no API keys) and verifies the whole pipeline —
signals → backtest → risk → gate → paper execution → state.json → trade log.

Run:  python -m tests.test_cycle_offline
"""
import asyncio
import json
import os
import sys
import tempfile

os.environ.setdefault("PAPER_TRADING", "true")
os.environ.setdefault("ANTHROPIC_API_KEY", "")  # force quantitative-only gating

# Run in a scratch dir so state.json / trades.db don't pollute the repo
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
_WORKDIR = tempfile.mkdtemp(prefix="polytest-e2e-")
os.chdir(_WORKDIR)

import numpy as np
import pandas as pd

import config

assert config.PAPER_TRADING, "test must run in paper mode"
config.LLM_REVIEW_ENABLED = False  # explicit, regardless of ambient env

from agents.data_agent import DataAgent
from agents.macro_agent import MacroAgent
from data.trade_log import get_alltime_stats, get_last_cycle, init as init_trade_log, record as record_trade
from orchestrator import TradingOrchestrator


def synthetic_market_data() -> dict:
    idx = pd.date_range(end="2026-07-01", periods=1825, freq="D")
    rng = np.random.default_rng(7)
    # Upward-drifting random walk: produces enough signal for a paper trade
    prices = 30_000 * np.exp(np.cumsum(rng.normal(0.001, 0.015, len(idx))))
    df = pd.DataFrame(
        {
            "open": prices,
            "high": prices * 1.01,
            "low": prices * 0.99,
            "close": prices,
            "volume": rng.uniform(1e3, 1e4, len(idx)),
        },
        index=idx,
    )
    return {
        "daily": df.to_dict(),
        "current_price": float(prices[-1]),
        "symbol": "BTCUSDT",
        "fetched_at": "2026-07-01T00:00:00+00:00",
    }


def synthetic_macro() -> dict:
    return {
        "fear_greed": {"value": 35, "label": "Fear"},
        "fear_greed_signal": 1,
        "funding_rate": -0.0002,
        "funding_signal": 1,
        "open_interest": 90_000.0,
        "fetched_at": "2026-07-01T00:00:00+00:00",
    }


async def run() -> dict:
    # Inject fixtures in place of the network-bound agents
    data = synthetic_market_data()
    macro = synthetic_macro()

    async def fake_data_run(self):
        return data

    async def fake_macro_run(self):
        return macro

    DataAgent.run = fake_data_run
    MacroAgent.run = fake_macro_run

    orchestrator = TradingOrchestrator()
    results = await orchestrator.run_cycle()

    # ── Assertions over the completed cycle ──────────────────────────────
    assert results["signals"]["current_position"] in (-1, 0, 1)
    assert "error" not in results["backtest"], results["backtest"]
    assert results["backtest"]["total_trades"] > 0
    assert "approved" in results["risk"]
    assert results["review"].get("skipped") is True
    status = results["execution"]["status"]
    assert status in ("paper_trade", "no_trade", "blocked"), status

    # state.json + trade log round-trip, exactly like main.py does it
    init_trade_log()
    state = {
        "cycle": get_last_cycle() + 1,
        "timestamp": "2026-07-01T01:00:00+00:00",
        "execution": results["execution"],
        "risk_score": results["orchestrator_review"].get("risk_score", 0),
        "signal": results["signals"]["current_position"],
        "btc_price": results["data"]["current_price"],
        "fear_greed_value": results["macro"]["fear_greed"]["value"],
    }
    with open(config.STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)
    record_trade(state)

    stats = get_alltime_stats()
    assert stats["total_cycles"] == 1, stats
    with open(config.STATE_FILE) as f:
        assert json.load(f)["cycle"] == 1

    # ── Force the paper-execution path (BUY signal, all gates approved) ──
    from agents.execution_agent import ExecutionAgent

    forced = {
        "signals": {"current_position": 1},
        "data": {"current_price": data["current_price"]},
        "risk": {"approved": True, "position_size": 0.05},
        "review": {"approved": True},
    }
    trade = await ExecutionAgent(forced).run()
    assert trade["status"] == "paper_trade", trade
    assert trade["direction"] == "YES"
    assert 0 < trade["amount_usdc"] <= config.PAPER_BALANCE * 0.10
    assert trade["market"], "paper trade must reference a market (live or simulated)"
    results["forced_paper_trade"] = trade

    return results


if __name__ == "__main__":
    results = asyncio.run(run())
    ex = results["execution"]
    print("\n════════ E2E RESULT ════════")
    print(f"signal:    {results['signals']['current_position']}")
    print(f"backtest:  return={results['backtest']['total_return_pct']:.1f}% "
          f"sharpe={results['backtest']['sharpe_ratio']:.2f} "
          f"maxDD={results['backtest']['max_drawdown_pct']:.1f}%")
    print(f"risk:      approved={results['risk']['approved']} score={results['risk']['risk_score']}")
    print(f"execution: {ex['status']}" + (f" — {ex.get('direction')} ${ex.get('amount_usdc')} on '{ex.get('market', '')[:50]}'" if ex.get('direction') else ""))
    print("ALL ASSERTIONS PASSED ✅")
