import json

import httpx
import pytest

from langchain_swapchan import SwapChanClient, SwapChanToolkit, UnverifiedTxError, to_base_units


def tk(body, status=200, seen=None):
    def handler(req):
        if seen is not None:
            seen.append(req)
        return httpx.Response(status, json=body)
    return SwapChanToolkit(client=SwapChanClient(partner="p1", transport=httpx.MockTransport(handler)))


def tool(t, name):
    return next(x for x in t.get_tools() if x.name == name)


def test_tools():
    assert len(SwapChanToolkit().get_tools()) == 13
    assert to_base_units("1.5", 6) == "1500000"


def test_verified_build():
    seen = []
    r = json.loads(tool(tk({"to": "0xr", "data": "0x", "verified": True}, seen=seen), "swapchan_build_swap_tx").invoke({"quote_id": "q", "taker": "0xa"}))
    assert r["verified"] is True
    assert json.loads(seen[0].content) == {"quoteId": "q", "taker": "0xa"}


@pytest.mark.parametrize("body,status", [({"to": "0xr"}, 200), ({"to": "0xr", "verified": False}, 200), ({"error": "x", "verified": False}, 502)])
def test_unverified_refused(body, status):
    with pytest.raises(UnverifiedTxError):
        tool(tk(body, status), "swapchan_build_swap_tx").invoke({"quote_id": "q", "taker": "0xa"})


def test_partner_passed():
    seen = []
    t = tk({"quotes": [], "best": None, "errors": []}, seen=seen)
    t.client._tokens[1] = [{"address": "0xa", "symbol": "ETH", "decimals": 18}, {"address": "0xb", "symbol": "USDC", "decimals": 6}]
    tool(t, "swapchan_get_quotes").invoke({"from_chain": "ethereum", "from_token": "ETH", "to_token": "USDC", "amount": "1"})
    assert seen[0].url.params["partner"] == "p1"


def test_live_quotes():
    r = json.loads(tool(SwapChanToolkit(), "swapchan_get_quotes").invoke({"from_chain": "ethereum", "from_token": "ETH", "to_token": "USDC", "amount": "0.1"}))
    assert r["quotes"] and float(r["quotes"][0]["toAmount"]) > 50
