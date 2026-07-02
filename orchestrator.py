import asyncio
import json

import anthropic

from config import CLAUDE_MODEL
from llm_utils import extract_json
from agents.data_agent import DataAgent
from agents.macro_agent import MacroAgent
from agents.signal_agent import SignalAgent
from agents.backtest_agent import BacktestAgent
from agents.risk_agent import RiskAgent
from agents.execution_agent import ExecutionAgent
from agents.review_agent import ReviewAgent
from agents.notifier import Notifier


class TradingOrchestrator:
    """
    Claude as the brain: Dispatch → Execute → Review.

    Each cycle builds a fresh results dict; the completed cycle is published
    to self.results atomically at the end so outside readers (daily summary)
    never see a half-built cycle.
    """

    def __init__(self):
        self.client = anthropic.AsyncAnthropic()
        self.results: dict = {}

    async def review_all(self, results: dict) -> dict:
        # Slim payload: drop raw market data, per-day indicator rows, and the
        # equity curve — the reviewer only needs the aggregate metrics.
        safe = {
            "signals": {k: v for k, v in results.get("signals", {}).items() if k != "signals"},
            "backtest": {k: v for k, v in results.get("backtest", {}).items() if k != "equity_curve"},
            "risk": results.get("risk", {}),
            "review": results.get("review", {}),
            "macro": results.get("macro", {}),
        }
        try:
            resp = await self.client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Review these trading results and flag drift or issues:\n"
                            f"{json.dumps(safe, indent=2, default=str)}\n\n"
                            "Return JSON: {approved, issues, recommendations, kill_agents, risk_score}"
                        ),
                    }
                ],
            )
            parsed = extract_json(resp.content[0].text)
            if isinstance(parsed, dict):
                return parsed
            print("[ORCHESTRATOR] review_all: no JSON in response")
        except Exception as e:
            print(f"[ORCHESTRATOR] review_all failed: {e}")
        return {"approved": False, "issues": ["review failed"], "risk_score": 100}

    async def run_cycle(self) -> dict:
        results: dict = {}
        print("\n[ORCHESTRATOR] ═══ TRADING CYCLE START ═══")

        print("[ORCHESTRATOR] 1/5 Fetching market data + macro in parallel...")
        data_result, macro_result = await asyncio.gather(
            DataAgent().run(),
            MacroAgent().run(),
        )
        results["data"] = data_result
        results["macro"] = macro_result

        print("[ORCHESTRATOR] 2/5 Generating signals...")
        results["signals"] = await SignalAgent(results["data"], results["macro"]).run()

        print("[ORCHESTRATOR] 3/5 Running 5-year backtest...")
        results["backtest"] = await BacktestAgent(results["data"], results["signals"]).run()

        # Risk must complete before review: the reviewer's verdict gates
        # execution and has to be based on the current cycle's risk assessment.
        print("[ORCHESTRATOR] 4/5 Risk assessment, then Claude review...")
        results["risk"] = await RiskAgent(results["backtest"]).run()
        results["review"] = await ReviewAgent(results).run()

        print("[ORCHESTRATOR] 5/5 Final review and execution...")
        orchestrator_review = await self.review_all(results)
        results["orchestrator_review"] = orchestrator_review

        notifier = Notifier()
        risk_score = orchestrator_review.get("risk_score", 100)
        if risk_score > 70:
            print(f"[ORCHESTRATOR] HIGH RISK ({risk_score}/100) — blocked")
            results["execution"] = {"status": "blocked", "reason": f"risk score {risk_score}"}
            await notifier.send_risk_alert(risk_score, orchestrator_review.get("issues", []))
        elif results["review"].get("approved") and results["risk"].get("approved"):
            print("[ORCHESTRATOR] Approved — executing...")
            results["execution"] = await ExecutionAgent(results).run()
        else:
            print("[ORCHESTRATOR] Not approved — no trade")
            results["execution"] = {"status": "no_trade", "reason": "not approved"}

        await notifier.send_trade_alert(results["execution"], results)

        self.results = results
        print("[ORCHESTRATOR] ═══ CYCLE COMPLETE ═══\n")
        return results
