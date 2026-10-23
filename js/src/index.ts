import { BaseToolkit, tool, type StructuredToolInterface } from "@langchain/core/tools";
import { SwapChanClient, type SwapChanClientOptions } from "./client.js";
import { SPECS } from "./specs.js";
export * from "./client.js";
export { SPECS, type ToolSpec } from "./specs.js";

/** SwapChan tools as LangChain.js structured tools. */
export function swapchanTools(opts: SwapChanClientOptions & { client?: SwapChanClient } = {}): StructuredToolInterface[] {
  const client = opts.client ?? new SwapChanClient(opts);
  return SPECS.map((s) =>
    tool(async (input: any) => JSON.stringify(await s.run(client, input)), { name: s.name, description: s.description, schema: s.schema }) as any,
  );
}

/** LangChain toolkit: `new SwapChanToolkit({ partner }).getTools()`. */
export class SwapChanToolkit extends BaseToolkit {
  tools: StructuredToolInterface[];
  constructor(opts: SwapChanClientOptions & { client?: SwapChanClient } = {}) {
    super();
    this.tools = swapchanTools(opts);
  }
}
