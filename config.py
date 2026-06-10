import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
POLYMARKET_PRIVATE_KEY = os.getenv("POLYMARKET_PRIVATE_KEY", "")
POLYMARKET_API_KEY = os.getenv("POLYMARKET_API_KEY", "")
POLYMARKET_API_SECRET = os.getenv("POLYMARKET_API_SECRET", "")
POLYMARKET_PASSPHRASE = os.getenv("POLYMARKET_PASSPHRASE", "")

PAPER_TRADING = os.getenv("PAPER_TRADING", "true").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

SYMBOL = "BTCUSDT"
BACKTEST_YEARS = 5
MAX_POSITION_SIZE = 0.10   # 10% of portfolio per trade
MAX_DRAWDOWN_LIMIT = -0.20  # Halt if drawdown exceeds 20%
MIN_SHARPE_RATIO = 0.5
CLAUDE_MODEL = "claude-fable-5"
POLYMARKET_HOST = "https://clob.polymarket.com"
POLYGON_CHAIN_ID = 137
CYCLE_INTERVAL_SECONDS = 3600  # Run every hour
