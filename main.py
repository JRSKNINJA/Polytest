import asyncio
import json
import logging
import signal
import sys
from datetime import datetime

from config import CYCLE_INTERVAL_SECONDS, LOG_LEVEL, PAPER_TRADING
from orchestrator import TradingOrchestrator

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

_running = True


def _handle_signal(signum, frame):
    global _running
    print("\n[MAIN] Shutdown requested...")
    _running = False


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


async def main():
    mode = "PAPER" if PAPER_TRADING else "LIVE"
    print(f"""
╔══════════════════════════════════════════════════════╗
║     BTC/Polymarket Multi-Agent Trading Bot           ║
║     Mode: {mode:<43}║
║     Cycle: every {CYCLE_INTERVAL_SECONDS}s{' '*(41-len(str(CYCLE_INTERVAL_SECONDS)))}║
╚══════════════════════════════════════════════════════╝
""")

    orchestrator = TradingOrchestrator()
    cycle = 0

    while _running:
        cycle += 1
        print(f"[MAIN] Cycle #{cycle} starting at {datetime.now().isoformat()}")

        try:
            results = await orchestrator.run_cycle()

            state = {
                "cycle": cycle,
                "timestamp": datetime.now().isoformat(),
                "execution": results.get("execution", {}),
                "risk_score": results.get("orchestrator_review", {}).get("risk_score", 0),
                "signal": results.get("signals", {}).get("current_position", 0),
                "btc_price": results.get("data", {}).get("current_price", 0),
                "fear_greed_value": results.get("macro", {}).get("fear_greed", {}).get("value", 50),
            }

            with open("state.json", "w") as f:
                json.dump(state, f, indent=2, default=str)

            print(f"[MAIN] Cycle #{cycle} done. Next in {CYCLE_INTERVAL_SECONDS}s.")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[MAIN] Cycle #{cycle} error: {e}")

        if _running:
            await asyncio.sleep(CYCLE_INTERVAL_SECONDS)

    print("[MAIN] Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
