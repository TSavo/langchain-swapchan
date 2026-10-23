# langchain-swapchan

[LangChain](https://langchain.com) tools for [SwapChan](https://swapchan.com), in **Python** (`python/`, PyPI `langchain-swapchan`) and **JavaScript** (`js/`, npm `langchain-swapchan`): best-price same-chain and cross-chain swap quotes across every DEX aggregator and bridge (Jupiter, 1inch, 0x, CoW, LI.FI, Relay, KyberSwap, Velora, Across, deBridge, THORChain), server-verified unsigned transactions, and free chain readers. No API key.

## Python

```bash
pip install langchain-swapchan
```

```python
from langchain_swapchan import SwapChanToolkit
from langchain.agents import create_agent

tools = SwapChanToolkit(partner="your-partner-id").get_tools()
agent = create_agent("openai:gpt-5", tools)
agent.invoke({"messages": [("user", "Best price for 1 ETH on Base to USDC on Arbitrum?")]})
```

## JavaScript

```bash
npm i langchain-swapchan @langchain/core zod
```

```ts
import { SwapChanToolkit } from "langchain-swapchan";
import { createAgent } from "langchain";

const agent = createAgent({ model: "openai:gpt-5", tools: new SwapChanToolkit({ partner: "your-partner-id" }).getTools() });
await agent.invoke({ messages: [{ role: "user", content: "Best price for 1 ETH on Base to USDC on Arbitrum?" }] });
```

## Tools

`swapchan_get_quotes`, `swapchan_build_swap_tx`, `swapchan_swap_status`, `swapchan_list_chains`, `swapchan_resolve_token`, `swapchan_wallet_balances`, `swapchan_token_approvals`, `swapchan_revoke_approval_tx`, `swapchan_explain_tx`, `swapchan_gas`, `swapchan_token_info`, `swapchan_resolve_name`, `swapchan_yields`. Quotes take human amounts and token symbols or addresses. Tools return JSON text.

## Safety

SwapChan never holds keys. `swapchan_build_swap_tx` returns an unsigned transaction for the user's own wallet. The SwapChan server decodes the calldata first and checks the router/spender is on a per-chain allowlist, the recipient is the user, minOut matches the quote, and approvals are capped at the sell amount. The response carries `verified` and `verification`; both packages raise `UnverifiedTxError` and return nothing unless `verified` is true.

## Make money with SwapChan

Register a partner id at [swapchan.com/partners](https://swapchan.com/partners) (or `POST https://api.swapchan.com/partners`) and pass `partner=` to the toolkit or per quote. You earn **5 bp (half of SwapChan's 0.1% fee) on every swap your agent routes**: $1M routed = $500 to your wallet. Details: [swapchan.com/earn](https://swapchan.com/earn).

## Tests

- Python: `cd python && uv run --group dev pytest`
- JS: `cd js && npm i && npm test`

Builds are tested with mocks (including refusal of unverified txs); quotes hit the live API.

Also: [Vercel AI SDK tools](https://github.com/TSavo/swapchan-ai-sdk), [ElizaOS plugin](https://github.com/TSavo/plugin-swapchan), MCP server at `https://mcp.swapchan.com/mcp`.

MIT
