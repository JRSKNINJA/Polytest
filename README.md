# Polytest — BTC/Polymarket Multi-Agent Trading Bot

A BTC prediction-market trading bot powered by a pipeline of Claude agents.
Runs out of the box in paper mode with **zero API keys** — add keys to unlock
LLM review, Telegram alerts, and live execution.

## Architecture

```
Orchestrator (per hourly cycle)
       ↓
  DataAgent ──┐
               ├─ parallel ──→ SignalAgent ──→ BacktestAgent (5y)
  MacroAgent ─┘                                     ↓
                                               RiskAgent (quant gates)
                                                    ↓
                                               ReviewAgent (Claude QA)
                                                    ↓
                                          Orchestrator review + gate
                                                    ↓
                                     ExecutionAgent (Polymarket CLOB)
                                                    ↓
                                     Notifier (Telegram, every cycle)
```

- **DataAgent** — 5 years of BTC daily OHLCV from Binance (public API, no key needed)
- **MacroAgent** — Fear & Greed index, Binance funding rate, open interest
- **SignalAgent** — RSI/MACD/Bollinger/trend composite + macro boost
- **BacktestAgent** — full-history backtest: Sharpe, drawdown, win rate
- **RiskAgent** — quantitative gates; shrinks position size on weak metrics
- **ReviewAgent** — Claude reviews all agent outputs before any trade
- **ExecutionAgent** — paper trades by default; live orders on the Polymarket CLOB

## Quickstart (paper mode, no keys)

```bash
pip install -r requirements.txt
python main.py
```

That's it. The bot fetches real Binance data, runs the full pipeline hourly,
simulates trades with a virtual `PAPER_BALANCE` (default $1,000), and writes
`state.json` + `trades.db`.

Verify the install without any network access:

```bash
python -m tests.test_cycle_offline
```

## Run with the dashboard (Docker)

With [GCM-AMP](../GCM-AMP) cloned as a sibling directory:

```bash
cp .env.example .env   # optional keys
docker compose up -d --build
# dashboard at http://localhost:8000
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `PAPER_TRADING` | no | `true` (default) = simulated; `false` = live orders |
| `PAPER_BALANCE` | no | Simulated USDC balance in paper mode (default 1000) |
| `ANTHROPIC_API_KEY` | for LLM review | Without it, gating is quantitative-only |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | for alerts | Per-cycle + daily summary messages |
| `BINANCE_API_KEY` / `BINANCE_API_SECRET` | no | Public market data works without keys |
| `POLYMARKET_PRIVATE_KEY` | for live | Ethereum wallet key (USDC on Polygon) |
| `POLYMARKET_API_KEY` / `_SECRET` / `_PASSPHRASE` | for live | Polymarket CLOB credentials |
| `STATE_FILE` / `TRADES_DB` | no | Output paths (used by Docker) |

## Signal Logic

- **RSI** (30/70 thresholds) — 30% weight
- **MACD histogram** crossover — 30% weight
- **Bollinger Band** mean reversion — 20% weight
- **SMA 20/50 trend** — 20% weight
- **Macro boost** — Fear & Greed ±0.15, funding rate ±0.10

Composite score > 0.3 → BUY, < -0.3 → SELL, else FLAT.

## Risk Gates

All must pass before any trade:

1. **Quantitative** — Sharpe ≥ 0.5, drawdown ≤ 20%, win rate ≥ 45%, positive return
2. **Claude review** — LLM sanity check of all agent outputs (when key configured)
3. **Orchestrator score** — cycles with risk score > 70 are blocked and alerted

## Going live — checklist

1. Run paper mode for several days; watch the dashboard and Telegram alerts
2. Fund your Polygon wallet with USDC and set the four `POLYMARKET_*` vars
3. Set `ANTHROPIC_API_KEY` so the LLM review gate is active
4. Set `PAPER_TRADING=false` and restart

Position sizing is capped at 10% of balance per trade, halved/quartered
automatically when backtest metrics weaken.

> **Not financial advice.** Prediction markets can lose your entire stake.
> Only trade funds you can afford to lose.
