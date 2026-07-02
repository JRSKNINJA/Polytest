import json

import anthropic

from config import CLAUDE_MODEL
from llm_utils import extract_json
from .base_agent import BaseAgent


class ReviewAgent(BaseAgent):
    def __init__(self, all_results: dict):
        super().__init__("ReviewAgent")
        self.results = all_results
        self.client = anthropic.AsyncAnthropic()

    async def run(self) -> dict:
        self.log("Claude is reviewing all agent outputs...")

        summary = {
            "data": {
                "current_price": self.results.get("data", {}).get("current_price"),
                "symbol": self.results.get("data", {}).get("symbol"),
            },
            "signals": {
                k: v
                for k, v in self.results.get("signals", {}).items()
                if k not in ("signals",)
            },
            "backtest": {
                k: v
                for k, v in self.results.get("backtest", {}).items()
                if k != "equity_curve"
            },
            "risk": {
                k: v
                for k, v in self.results.get("risk", {}).items()
            },
        }

        try:
            response = await self.client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": f"""You are a senior quant risk manager reviewing multi-agent trading outputs.

Agent results:
{json.dumps(summary, indent=2, default=str)}

Review for: signal/backtest consistency, risk validity, overfitting red flags, execution readiness.

Return ONLY valid JSON:
{{
  "approved": <bool>,
  "confidence": <0-100>,
  "issues": ["..."],
  "red_flags": ["..."],
  "recommendation": "...",
  "kill_agents": []
}}""",
                    }
                ],
            )
            result = extract_json(response.content[0].text)
            if isinstance(result, dict):
                self.log(f"Review: approved={result.get('approved')}, confidence={result.get('confidence')}")
                return result
        except Exception as e:
            self.log(f"Review failed: {e}")

        return {
            "approved": False,
            "confidence": 0,
            "issues": ["Review agent failed"],
            "red_flags": [],
            "recommendation": "Do not trade",
            "kill_agents": [],
        }
