from config import (
    POLYGON_CHAIN_ID,
    POLYMARKET_API_KEY,
    POLYMARKET_API_SECRET,
    POLYMARKET_HOST,
    POLYMARKET_PASSPHRASE,
    POLYMARKET_PRIVATE_KEY,
)


def _levels(levels) -> list[dict]:
    out = []
    for level in levels or []:
        if isinstance(level, dict):
            out.append({"price": level.get("price", 0), "size": level.get("size", 0)})
        else:
            out.append({"price": getattr(level, "price", 0), "size": getattr(level, "size", 0)})
    return out


class PolymarketClient:
    def __init__(self):
        try:
            from py_clob_client.client import ClobClient
            from py_clob_client.clob_types import ApiCreds

            self._client = ClobClient(
                POLYMARKET_HOST,
                key=POLYMARKET_PRIVATE_KEY,
                chain_id=POLYGON_CHAIN_ID,
                creds=ApiCreds(
                    api_key=POLYMARKET_API_KEY,
                    api_secret=POLYMARKET_API_SECRET,
                    api_passphrase=POLYMARKET_PASSPHRASE,
                ),
            )
        except Exception as e:
            self._client = None
            print(f"[PolymarketClient] Init failed (credentials missing?): {e}")

    def _require_client(self):
        if self._client is None:
            raise RuntimeError("Polymarket client not initialized. Check credentials.")

    def get_markets(self, next_cursor: str = "MA==") -> dict:
        self._require_client()
        return self._client.get_markets(next_cursor=next_cursor)

    def get_market(self, condition_id: str) -> dict:
        self._require_client()
        return self._client.get_market(condition_id)

    def get_orderbook(self, token_id: str) -> dict:
        """Return the order book normalized to {"asks": [...], "bids": [...]}.

        py-clob-client returns an OrderBookSummary dataclass, not a dict —
        normalize so callers can rely on plain dict access.
        """
        self._require_client()
        book = self._client.get_order_book(token_id)
        if isinstance(book, dict):
            return {"asks": _levels(book.get("asks")), "bids": _levels(book.get("bids"))}
        return {"asks": _levels(getattr(book, "asks", [])), "bids": _levels(getattr(book, "bids", []))}

    def place_order(self, token_id: str, price: float, size: float, side: str) -> dict:
        self._require_client()
        from py_clob_client.clob_types import OrderArgs

        args = OrderArgs(price=price, size=size, side=side, token_id=token_id)
        return self._client.create_and_post_order(args)

    def get_balance(self) -> dict:
        self._require_client()
        from py_clob_client.clob_types import BalanceAllowanceParams

        return self._client.get_balance_allowance(
            params=BalanceAllowanceParams(asset_type="COLLATERAL")
        )
