import { describe, expect, it } from "vitest";
import { SwapChanToolkit, UnverifiedTxError } from "../src/index.js";

const json = (b: unknown, status = 200) => new Response(JSON.stringify(b), { status });
const mockFetch = (b: unknown, status = 200) => (async () => json(b, status)) as unknown as typeof fetch;
const get = (tk: SwapChanToolkit, n: string) => tk.getTools().find((t) => t.name === n)!;

describe("SwapChanToolkit", () => {
  it("has 13 tools", () => expect(new SwapChanToolkit().getTools().length).toBe(13));
  it("returns verified builds", async () => {
    const tk = new SwapChanToolkit({ fetch: mockFetch({ to: "0xr", data: "0x", value: "0", verified: true }) });
    const r = JSON.parse(await get(tk, "swapchan_build_swap_tx").invoke({ quoteId: "q", taker: "0xa" }));
    expect(r.verified).toBe(true);
  });
  it("refuses unverified builds", async () => {
    for (const [b, s] of [[{ to: "0xr" }, 200], [{ to: "0xr", verified: false }, 200], [{ error: "x", verified: false }, 502]] as const) {
      const tk = new SwapChanToolkit({ fetch: mockFetch(b, s) });
      await expect(get(tk, "swapchan_build_swap_tx").invoke({ quoteId: "q", taker: "0xa" })).rejects.toBeInstanceOf(UnverifiedTxError);
    }
  });
  it("live quotes ETH -> USDC", async () => {
    const r = JSON.parse(await get(new SwapChanToolkit(), "swapchan_get_quotes").invoke({ fromChain: "ethereum", fromToken: "ETH", toToken: "USDC", amount: "0.1" }));
    expect(r.quotes.length).toBeGreaterThan(0);
  }, 40_000);
});
