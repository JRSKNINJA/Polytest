import sqlite3
from datetime import date, datetime

DB = "trades.db"


def init():
    con = sqlite3.connect(DB)
    con.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle       INTEGER UNIQUE,
            timestamp   TEXT,
            status      TEXT,
            signal      INTEGER,
            btc_price   REAL,
            amount_usdc REAL,
            market      TEXT,
            risk_score  INTEGER,
            fear_greed  INTEGER,
            direction   TEXT
        )
    """)
    con.commit()
    con.close()


def record(state: dict):
    execution = state.get("execution", {})
    con = sqlite3.connect(DB)
    con.execute(
        """INSERT OR IGNORE INTO trades
           (cycle,timestamp,status,signal,btc_price,amount_usdc,market,risk_score,fear_greed,direction)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            state.get("cycle", 0),
            state.get("timestamp", datetime.now().isoformat()),
            execution.get("status", ""),
            state.get("signal", 0),
            state.get("btc_price", 0),
            execution.get("amount_usdc", 0),
            (execution.get("market") or "")[:200],
            state.get("risk_score", 0),
            state.get("fear_greed_value", 50),
            execution.get("direction", ""),
        ),
    )
    con.commit()
    con.close()


def get_today() -> list[dict]:
    today = date.today().isoformat()
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT * FROM trades WHERE timestamp LIKE ? ORDER BY id",
        (f"{today}%",),
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]


def get_alltime_stats() -> dict:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    row = con.execute("""
        SELECT
            COUNT(*)                                                          AS total_cycles,
            SUM(CASE WHEN status IN ('paper_trade','executed') THEN 1 ELSE 0 END) AS total_trades,
            COALESCE(SUM(CASE WHEN status IN ('paper_trade','executed') THEN amount_usdc ELSE 0 END), 0) AS total_deployed,
            AVG(risk_score)                                                   AS avg_risk,
            MIN(btc_price)                                                    AS btc_low,
            MAX(btc_price)                                                    AS btc_high
        FROM trades
    """).fetchone()
    con.close()
    return dict(row) if row else {}
