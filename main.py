import asyncio
import json
import logging
import signal
from datetime import datetime, timedelta, timezone

from config import CYCLE_INTERVAL_SECONDS, LOG_LEVEL, PAPER_TRADING
from data.trade_log import (
    get_alltime_stats,
    get_last_cycle,
    get_today,
    init as init_trade_log,
    record as record_trade,
)
from orchestrator import TradingOrchestrator

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)


async def daily_summary_loop(get_results_fn):
    """Fires once per day at midnight UTC. Errors are logged, never fatal —
    one failed summary must not kill all future ones."""
    from agents.notifier import Notifier

    while True:
        now = datetime.now(timezone.utc)
        tomorrow_midnight = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        await asyncio.sleep((tomorrow_midnight - now).total_seconds())

        try:
            trades = get_today()
            stats = get_alltime_stats()
            results = get_results_fn()
            current_price = results.get("data", {}).get("current_price", 0) if results else 0
            await Notifier().send_daily_summary(trades, stats, current_price)
        except Exception as e:
            print(f"[MAIN] Daily summary failed: {e}")


async def main():
    mode = "PAPER" if PAPER_TRADING else "LIVE"
    print(f"""
╔══════════════════════════════════════════════════════╗
║     BTC/Polymarket Multi-Agent Trading Bot           ║
║     Mode: {mode:<43}║
║     Cycle: every {CYCLE_INTERVAL_SECONDS}s{' '*(41-len(str(CYCLE_INTERVAL_SECONDS)))}║
╚══════════════════════════════════════════════════════╝
""")

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # e.g. Windows
            signal.signal(sig, lambda *_: stop.set())

    init_trade_log()

    orchestrator = TradingOrchestrator()
    summary_task = asyncio.create_task(daily_summary_loop(lambda: orchestrator.results))

    # Resume the cycle counter across restarts so trade_log's UNIQUE(cycle)
    # keeps deduping instead of silently dropping every new row.
    cycle = get_last_cycle()

    while not stop.is_set():
        cycle += 1
        print(f"[MAIN] Cycle #{cycle} starting at {datetime.now(timezone.utc).isoformat()}")

        try:
            results = await orchestrator.run_cycle()

            state = {
                "cycle": cycle,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "execution": results.get("execution", {}),
                "risk_score": results.get("orchestrator_review", {}).get("risk_score", 0),
                "signal": results.get("signals", {}).get("current_position", 0),
                "btc_price": results.get("data", {}).get("current_price", 0),
                "fear_greed_value": results.get("macro", {}).get("fear_greed", {}).get("value", 50),
            }

            with open("state.json", "w") as f:
                json.dump(state, f, indent=2, default=str)

            record_trade(state)

            print(f"[MAIN] Cycle #{cycle} done. Next in {CYCLE_INTERVAL_SECONDS}s.")
        except Exception as e:
            print(f"[MAIN] Cycle #{cycle} error: {e}")

        # Wake immediately on shutdown instead of sleeping out the interval
        try:
            await asyncio.wait_for(stop.wait(), timeout=CYCLE_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            pass

    summary_task.cancel()
    print("[MAIN] Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
