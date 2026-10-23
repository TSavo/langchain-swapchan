"""SwapChan tools for LangChain (langchain-core BaseTool / BaseToolkit)."""
from __future__ import annotations

import json
from typing import Any, Callable, List, Optional, Type, Union

from langchain_core.tools import BaseTool, BaseToolkit
from pydantic import BaseModel, ConfigDict, Field

from .client import SwapChanClient, chain_id, from_base_units, to_base_units

Chain = Union[str, int]
SAFETY = "SwapChan never holds keys. Show the tx to the user and sign only with their wallet."
CHAIN_DESC = 'Chain name ("base", "solana") or numeric chain id'


class QuoteInput(BaseModel):
    from_chain: Chain = Field(description=CHAIN_DESC)
    to_chain: Optional[Chain] = Field(None, description="Destination chain; defaults to from_chain")
    from_token: str = Field(description="Symbol (ETH, USDC) or contract address/mint")
    to_token: str
    amount: str = Field(description='Human amount of from_token, e.g. "1.5"')
    from_address: Optional[str] = Field(None, description="Wallet that will sign")
    to_address: Optional[str] = None
    slippage_bps: Optional[int] = None
    partner: Optional[str] = Field(None, description="SwapChan partner id (earns 5 bp)")


class BuildInput(BaseModel):
    quote_id: str
    taker: str = Field(description="Address that will sign")
    recipient: Optional[str] = None


class StatusInput(BaseModel):
    provider: str
    tx_hash: str
    from_chain: Chain
    to_chain: Chain


class Empty(BaseModel):
    pass


class ChainToken(BaseModel):
    chain: Chain = Field(description=CHAIN_DESC)
    token: str


class Balances(BaseModel):
    address: str
    chains: Optional[List[Chain]] = None


class Approvals(BaseModel):
    owner: str
    chain: Chain


class Revoke(BaseModel):
    chain: Chain
    token: str
    spender: str


class TxHash(BaseModel):
    chain: Chain
    hash: str


class Gas(BaseModel):
    chains: Optional[List[Chain]] = None


class TokenAddr(BaseModel):
    chain: Chain
    address: str


class Name(BaseModel):
    q: str = Field(description="ENS/SNS name or address")


class Yields(BaseModel):
    asset: Optional[str] = None
    chain: Optional[Chain] = None
    min_tvl_usd: Optional[float] = None
    stablecoin_only: Optional[bool] = None
    limit: Optional[int] = None


def _csv(chains):
    return ",".join(str(chain_id(c)) for c in chains) if chains else None


def _quotes(c: SwapChanClient, i: QuoteInput):
    fc = chain_id(i.from_chain)
    tc = chain_id(i.to_chain) if i.to_chain is not None else fc
    f, t = c.resolve_token(fc, i.from_token), c.resolve_token(tc, i.to_token)
    r = c.quotes(fromChainId=fc, toChainId=tc, fromToken=f["address"], toToken=t["address"],
                 amount=to_base_units(i.amount, f["decimals"]), slippageBps=i.slippage_bps,
                 fromAddress=i.from_address, toAddress=i.to_address, partner=i.partner)
    d = t["decimals"]
    return {"best": r.get("best"), "errors": r.get("errors"), "quotes": [
        {"quoteId": q["id"], "provider": q["provider"], "toAmount": from_base_units(q["toAmount"], d),
         "toAmountMin": from_base_units(q["toAmountMin"], d), "symbol": t["symbol"], "gasUsd": q.get("gasUsd"),
         "feeUsd": q.get("feeUsd"), "netUsd": q.get("netUsd"), "etaSeconds": q.get("etaSeconds"),
         "verified": q.get("verified"), "swapUrl": q.get("swapUrl")} for q in r["quotes"][:8]]}


SPECS: list[tuple[str, str, Type[BaseModel], Callable[[SwapChanClient, Any], Any]]] = [
    ("swapchan_get_quotes", "Best-price swap/bridge quotes across every aggregator and bridge (Jupiter, 1inch, 0x, CoW, LI.FI, Relay, KyberSwap, Velora, Across, deBridge, THORChain), ranked best-first net of gas and fees.", QuoteInput, _quotes),
    ("swapchan_build_swap_tx", f"Build the unsigned transaction for a quote_id. The server decodes and verifies it (router allowlist, recipient, minOut, capped approvals); unverified transactions are never returned. {SAFETY}", BuildInput,
     lambda c, i: c.build(i.quote_id, i.taker, i.recipient)),
    ("swapchan_swap_status", "Status of a submitted swap or bridge.", StatusInput,
     lambda c, i: c.req("GET", "/status", {"provider": i.provider, "txHash": i.tx_hash, "fromChainId": chain_id(i.from_chain), "toChainId": chain_id(i.to_chain)})),
    ("swapchan_list_chains", "Chains SwapChan supports.", Empty, lambda c, i: c.req("GET", "/chains")),
    ("swapchan_resolve_token", "Resolve a token symbol or address to address+decimals on a chain.", ChainToken,
     lambda c, i: c.resolve_token(chain_id(i.chain), i.token)),
    ("swapchan_wallet_balances", "Native and token balances for a wallet across chains (read-only).", Balances,
     lambda c, i: c.onchain("/balances", address=i.address, chains=_csv(i.chains))),
    ("swapchan_token_approvals", "ERC-20 approvals an owner has granted on a chain, with risk flags.", Approvals,
     lambda c, i: c.onchain("/approvals", owner=i.owner, chainId=chain_id(i.chain))),
    ("swapchan_revoke_approval_tx", f"Unsigned tx that revokes a token approval. {SAFETY}", Revoke,
     lambda c, i: c.onchain("/revoke", chainId=chain_id(i.chain), token=i.token, spender=i.spender)),
    ("swapchan_explain_tx", "Decode and explain a transaction by hash.", TxHash,
     lambda c, i: c.onchain("/tx", chainId=chain_id(i.chain), hash=i.hash)),
    ("swapchan_gas", "Current gas prices.", Gas, lambda c, i: c.onchain("/gas", chains=_csv(i.chains))),
    ("swapchan_token_info", "On-chain token metadata and risk scan.", TokenAddr,
     lambda c, i: c.onchain("/token", chainId=chain_id(i.chain), address=i.address)),
    ("swapchan_resolve_name", "Resolve ENS/SNS names to addresses, or reverse-resolve an address.", Name,
     lambda c, i: c.onchain("/name", q=i.q)),
    ("swapchan_yields", "Top DeFi yields (DefiLlama) for an asset; SwapChan can swap you into the underlying.", Yields,
     lambda c, i: c.onchain("/yields", asset=i.asset, chainId=chain_id(i.chain) if i.chain is not None else None,
                            minTvlUsd=i.min_tvl_usd, limit=i.limit,
                            stablecoinOnly=None if i.stablecoin_only is None else str(i.stablecoin_only).lower())),
]


class SwapChanTool(BaseTool):
    """One SwapChan API call exposed as a LangChain tool. Returns JSON text."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    client: SwapChanClient
    fn: Callable[[SwapChanClient, Any], Any]

    def _run(self, **kwargs: Any) -> str:
        return json.dumps(self.fn(self.client, self.args_schema(**kwargs)))


def swapchan_tools(client: Optional[SwapChanClient] = None, **client_kwargs: Any) -> List[BaseTool]:
    c = client or SwapChanClient(**client_kwargs)
    return [SwapChanTool(name=n, description=d, args_schema=s, client=c, fn=f) for n, d, s, f in SPECS]


class SwapChanToolkit(BaseToolkit):
    """`SwapChanToolkit(partner="your-id").get_tools()`"""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    client: SwapChanClient = Field(default_factory=SwapChanClient)

    def __init__(self, partner: Optional[str] = None, client: Optional[SwapChanClient] = None, **kw: Any):
        super().__init__(client=client or SwapChanClient(partner=partner, **kw))

    def get_tools(self) -> List[BaseTool]:
        return swapchan_tools(self.client)
