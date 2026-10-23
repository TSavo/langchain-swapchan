"""Minimal client for the public SwapChan HTTP API (https://api.swapchan.com). No API key required."""
from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, Optional

import httpx

DEFAULT_BASE_URL = "https://api.swapchan.com"
CHAIN_IDS = {
    "ethereum": 1, "eth": 1, "mainnet": 1, "optimism": 10, "op": 10, "bnb": 56, "bsc": 56,
    "polygon": 137, "matic": 137, "base": 8453, "arbitrum": 42161, "arb": 42161,
    "avalanche": 43114, "avax": 43114, "solana": 792703809, "sol": 792703809,
}
_ADDR = re.compile(r"^(0x[0-9a-fA-F]{40}|[1-9A-HJ-NP-Za-km-z]{32,44})$")


class SwapChanError(Exception):
    def __init__(self, status: int, message: str, body: Any = None):
        super().__init__(message)
        self.status, self.body = status, body


class UnverifiedTxError(SwapChanError):
    """The server did not positively verify a built transaction; it is never returned."""

    def __init__(self, body: Any):
        super().__init__(502, "SwapChan did not verify this transaction (verified != true); refusing to return it", body)


def chain_id(c: Any) -> int:
    if isinstance(c, int):
        return c
    s = str(c).strip().lower()
    if s.isdigit():
        return int(s)
    if s not in CHAIN_IDS:
        raise ValueError(f'Unknown chain "{c}"; pass a numeric chain id')
    return CHAIN_IDS[s]


def to_base_units(amount: str, decimals: int) -> str:
    s = str(amount).strip()
    if not re.fullmatch(r"\d+(\.\d+)?", s):
        raise ValueError(f"Invalid amount: {amount}")
    whole, _, frac = s.partition(".")
    if len(frac) > decimals:
        raise ValueError(f"Too many decimals for token (max {decimals})")
    return str(int(whole + frac.ljust(decimals, "0")))


def from_base_units(amount: str, decimals: int) -> str:
    return format((Decimal(int(amount)) / (Decimal(10) ** decimals)).normalize(), "f")


class SwapChanClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, partner: Optional[str] = None,
                 api_key: Optional[str] = None, timeout: float = 25.0, transport: Optional[httpx.BaseTransport] = None):
        self.base_url = base_url.rstrip("/")
        self.partner = partner or None
        headers = {"accept": "application/json"}
        if api_key:
            headers["x-api-key"] = api_key
        self._http = httpx.Client(base_url=self.base_url, headers=headers, timeout=timeout, transport=transport)
        self._tokens: dict[int, list] = {}

    def req(self, method: str, path: str, params: Optional[dict] = None, json: Any = None) -> Any:
        params = {k: v for k, v in (params or {}).items() if v not in (None, "")}
        r = self._http.request(method, path, params=params, json=json)
        try:
            body = r.json() if r.content else None
        except ValueError:
            raise SwapChanError(r.status_code, f"SwapChan API returned non-JSON (HTTP {r.status_code})")
        if r.status_code >= 400:
            raise SwapChanError(r.status_code, (body or {}).get("error", f"HTTP {r.status_code}"), body)
        return body

    def resolve_token(self, chain: int, token: str) -> dict:
        s = token.strip()
        if chain not in self._tokens:
            self._tokens[chain] = self.req("GET", "/tokens", {"chainId": chain})
        for t in self._tokens[chain]:
            if t["address"].lower() == s.lower() or t["symbol"].lower() == s.lower():
                return t
        if _ADDR.match(s):
            return self.req("GET", "/token", {"chainId": chain, "address": s})
        raise ValueError(f'Unknown token "{s}" on chain {chain}; pass its contract address/mint')

    def quotes(self, **p: Any) -> dict:
        p.setdefault("partner", None)
        p["partner"] = p["partner"] or self.partner
        return self.req("GET", "/quotes", p)

    def build(self, quote_id: str, taker: str, recipient: Optional[str] = None) -> dict:
        body = {"quoteId": quote_id, "taker": taker, **({"recipient": recipient} if recipient else {})}
        try:
            out = self.req("POST", "/build", json=body)
        except SwapChanError as e:
            if isinstance(e.body, dict) and e.body.get("verified") is False:
                raise UnverifiedTxError(e.body) from e
            raise
        if not isinstance(out, dict) or out.get("verified") is not True:
            raise UnverifiedTxError(out)
        return out

    def onchain(self, path: str, **q: Any) -> Any:
        return self.req("GET", f"/onchain{path}", q)
