# Polytest — BTC/Polymarket Multi-Agent Trading Bot

A live BTC prediction-market trading bot powered by a swarm of Claude agents.

## Architecture

```
Claude Fable 5 (Orchestrator)
       ↓
  Task Decomposition
       ↓
  ┌────────────────────────────────────────┐
  │  DataAgent      → Binance OHLCV data   │
  │  SignalAgent    → RSI/MACD/BB signals  │
  │  BacktestAgent  → 5-year backtest      │
  │  RiskAgent      → Risk gating          │
  │  ReviewAgent    → Claude QA review     │
  │  ExecutionAgent → Polymarket trades    │
  └────────────────────────────────────────┘
       ↓
  Orchestrator Review (kills drifted agents)
       ↓
  Execute or Block
```

## Setup

```bash
cp .env.example .env
# Fill in your API keys
pip install -r requirements.txt
python main.py
```

## Environment Variables

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key |
| `BINANCE_API_KEY` | Binance API key (read-only is fine for data) |
| `BINANCE_API_SECRET` | Binance API secret |
| `POLYMARKET_PRIVATE_KEY` | Ethereum wallet private key |
| `POLYMARKET_API_KEY` | Polymarket CLOB API key |
| `POLYMARKET_API_SECRET` | Polymarket API secret |
| `POLYMARKET_PASSPHRASE` | Polymarket API passphrase |
| `PAPER_TRADING` | `true` = paper mode (default), `false` = live |

## Signal Logic

- **RSI** (30/70 thresholds) — 30% weight
- **MACD histogram** crossover — 30% weight
- **Bollinger Band** mean reversion — 20% weight
- **SMA 20/50 trend** — 20% weight

Composite score > 0.3 → BUY, < -0.3 → SELL, else FLAT.

## Risk Gates

- Sharpe ratio ≥ 0.5
- Max drawdown ≤ 20%
- Win rate ≥ 45%
- Claude Fable 5 review approval

All gates must pass before execution.
