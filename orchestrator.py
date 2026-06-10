import asyncio
import json
import re

import anthropic

from config import CLAUDE_MODEL
from agents.data_agent import DataAgent
from agents.signal_agent import SignalAgent
from agents.backtest_agent import BacktestAgent
from agents.risk_agent import RiskAgent
from agents.execution_agent import ExecutionAgent
from agents.review_agent import ReviewAgent


class TradingOrchestrator:
    """
    Claude claude-fable-5 as the brain:
    Decompose → Dispatch → Execute → Review
    """

    def __init__(self):
        self.client = anthropic.Anthropic()
        self.results: dict = {}

    def decompose_goal(self, goal: str) -> list[dict]:
        resp = self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"You are a quant trading architect. Decompose this goal into a task tree:\n{goal}\n\n"
                        "Return a JSON array of tasks. Each task has: id, name, agent_type "
                        "(data|signal|backtest|risk|execution|review), dependencies, params, priority(1-5).\n"
                        "Return ONLY valid JSON."
                    ),
                }
            ],
        )
        try:
            match = re.search(r"\[.*\]", resp.content[0].text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass
        return []

    def review_all(self, results: dict) -> dict:
        safe = {k: v for k, v in results.items() if k not in ("data",)}
        resp = self.client.messages.create(
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
        try:
            match = re.search(r"\{.*\}", resp.content[0].text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass
        return {"approved": False, "issues": ["parse error"], "risk_score": 100}

    async def run_cycle(self) -> dict:
        print("\n[ORCHESTRATOR] ═══ TRADING CYCLE START ═══")

        print("[ORCHESTRATOR] 1/5 Decomposing goal...")
        task_tree = self.decompose_goal(
            "Trade BTC prediction markets on Polymarket with strict risk management and 5-year backtest validation"
        )
        print(f"[ORCHESTRATOR] {len(task_tree)} tasks in tree")

        # Step 2: Data (must come first — everything depends on it)
        print("[ORCHESTRATOR] 2/5 Fetching market data + macro in parallel...")
        from agents.data_agent import DataAgent
        from agents.macro_agent import MacroAgent
        data_result, macro_result = await asyncio.gather(
            DataAgent().run(),
            MacroAgent().run(),
        )
        self.results["data"] = data_result
        self.results["macro"] = macro_result

        # Step 3: Signals (depends on data + macro; backtest depends on signals — must be sequential here)
        print("[ORCHESTRATOR] 3/5 Generating signals...")
        from agents.signal_agent import SignalAgent
        self.results["signals"] = await SignalAgent(self.results["data"], self.results["macro"]).run()

        # Step 4: Backtest + Risk in parallel (backtest uses data+signals; risk uses backtest — chain but backtest is the slow part)
        print("[ORCHESTRATOR] 4/5 Backtesting...")
        from agents.backtest_agent import BacktestAgent
        self.results["backtest"] = await BacktestAgent(self.results["data"], self.results["signals"]).run()

        print("[ORCHESTRATOR] 4b/5 Risk + Review in parallel...")
        from agents.risk_agent import RiskAgent
        from agents.review_agent import ReviewAgent
        risk_result, review_result = await asyncio.gather(
            RiskAgent(self.results["backtest"]).run(),
            ReviewAgent(self.results).run(),
        )
        self.results["risk"] = risk_result
        self.results["review"] = review_result

        # Step 5: Orchestrator review + execution
        print("[ORCHESTRATOR] 5/5 Final review and execution...")
        orchestrator_review = self.review_all(self.results)
        self.results["orchestrator_review"] = orchestrator_review

        risk_score = orchestrator_review.get("risk_score", 100)
        if risk_score > 70:
            print(f"[ORCHESTRATOR] HIGH RISK ({risk_score}/100) — blocked")
            self.results["execution"] = {"status": "blocked", "reason": f"risk score {risk_score}"}
        elif self.results["review"].get("approved") and self.results["risk"].get("approved"):
            print("[ORCHESTRATOR] Approved — executing...")
            from agents.execution_agent import ExecutionAgent
            from agents.notifier import Notifier
            exec_result = await ExecutionAgent(self.results).run()
            self.results["execution"] = exec_result
            await Notifier().send_trade_alert(exec_result, self.results)
        else:
            print("[ORCHESTRATOR] Not approved — no trade")
            self.results["execution"] = {"status": "no_trade", "reason": "not approved"}

        print("[ORCHESTRATOR] ═══ CYCLE COMPLETE ═══\n")
        return self.results
