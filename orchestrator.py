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

        print("[ORCHESTRATOR] 1/6 Decomposing goal...")
        task_tree = self.decompose_goal(
            "Trade BTC prediction markets on Polymarket with strict risk management and 5-year backtest validation"
        )
        print(f"[ORCHESTRATOR] Task tree: {len(task_tree)} tasks identified")

        print("[ORCHESTRATOR] 2/6 Fetching market data (Binance)...")
        data_agent = DataAgent()
        self.results["data"] = await data_agent.run()

        print("[ORCHESTRATOR] 3/6 Generating signals...")
        signal_agent = SignalAgent(self.results["data"])
        self.results["signals"] = await signal_agent.run()

        print("[ORCHESTRATOR] 4/6 Running 5-year backtest...")
        backtest_agent = BacktestAgent(self.results["data"], self.results["signals"])
        self.results["backtest"] = await backtest_agent.run()

        print("[ORCHESTRATOR] 5/6 Risk assessment...")
        risk_agent = RiskAgent(self.results["backtest"])
        self.results["risk"] = await risk_agent.run()

        print("[ORCHESTRATOR] 6/6 Claude review of all outputs...")
        review_agent = ReviewAgent(self.results)
        self.results["review"] = await review_agent.run()

        orchestrator_review = self.review_all(self.results)
        self.results["orchestrator_review"] = orchestrator_review

        risk_score = orchestrator_review.get("risk_score", 100)
        if risk_score > 70:
            print(f"[ORCHESTRATOR] HIGH RISK ({risk_score}/100) — execution blocked")
            self.results["execution"] = {"status": "blocked", "reason": f"risk score {risk_score}"}
        elif self.results["review"].get("approved") and self.results["risk"].get("approved"):
            print("[ORCHESTRATOR] Approved — executing on Polymarket...")
            exec_agent = ExecutionAgent(self.results)
            self.results["execution"] = await exec_agent.run()
        else:
            print("[ORCHESTRATOR] Not approved — no trade")
            self.results["execution"] = {"status": "no_trade", "reason": "not approved"}

        print("[ORCHESTRATOR] ═══ CYCLE COMPLETE ═══\n")
        return self.results
