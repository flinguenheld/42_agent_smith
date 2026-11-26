# MCP — The Implementation Plan (D3: D1 + D2 together)

## The goal

The LLM writes Python that calls tools, like `run_tests(...)`. Those tools
don't live in the sandbox. They live in a separate **MCP server**. The sandbox
code calls a stub, the host forwards the call to the server, and the result
comes back as a string.

```text
 worker (restricted, no network)        host (normal process)
┌──────────────────────────┐        ┌───────────────────────────────┐
│ run_tests(code=..., ...) │ToolCall│ Sandbox._call_tool            │
│   = stub (_make_tool)    │──────► │   → tools[name](**kwargs)     │
│                          │◄────── │          │                    │
└──────────────────────────┘ToolRes.│     McpClient ── stdio/HTTP ──┼─► MCP server
                                    └───────────────────────────────┘
```

The relay already exists (`sandbox/worker.py` `_make_tool`,
`sandbox/host.py` `_call_tool`). It already takes tool time out of the
sandbox timeout. **The worker does not change.** MCP is only host-side work.

What the subject asks:

- A client over **stdio** and **Streamable HTTP**.
- **Dynamic discovery** of tools, resources and prompts. It will be tested
  with an **unknown server**.
- A **sandbox manual** generated from the tool schemas, put in the system
  prompt.
- `final_answer` stays a sandbox built-in. It is **not** an MCP tool.
- `mcp_tools_mbpp.py` and `mcp_tools_swebench.py` at the **repo root**.
  They are tested on their own.

---

## Step 0 — Decide before coding

| Question | Options | Recommendation |
|---|---|---|
| Library | official `mcp` SDK, or our own JSON-RPC on `httpx` | SDK (`FastMCP` for servers, `ClientSession` for the client) |
| Async SDK, sync `Sandbox` | event loop in a background thread, or `asyncio.run` per call | background thread: the session stays open |
| Positional args (`run_tests(code, tests)`) | keyword only (say so in the manual), or map them with the schema order | keyword only first: no worker change |
| Resources and prompts | built-ins `list_resources()`, `read_resource(uri)`, `get_prompt(name)` | built-ins, listed in the manual |

The stdlib-only rule is about **sandbox security**, not MCP. The SDK is
allowed.

---

## Step 1 — The MBPP server: `mcp_tools_mbpp.py`

One tool: `run_tests(code, test_list)`. It returns a JSON string with
`success` (bool) and `output` (str).

```python
mcp = FastMCP("mbpp")

@mcp.tool()
def run_tests(code: str, test_list: list[str]) -> str:
    """Run code against test assertions."""
    ...

if __name__ == "__main__":
    mcp.run()          # stdio by default
```

**Key points**

- `FastMCP` builds the JSON schema from the type hints and the docstring.
  The docstring **is** the description the LLM will read.
- The tool runs untrusted code **outside** our sandbox. So it runs it with
  our own `execute()` (`sandbox/host.py`): same limits, no copy-paste.
- Check it alone with the MCP inspector before writing any client.

---

## Step 2 — The client over stdio: `mcp/client.py`

A small **sync** class around the async SDK.

```text
 McpClient                          server process
┌──────────────┐  initialize        ┌────────────┐
│ connect()    │ ─────────────────► │            │
│              │ ◄─ capabilities ── │            │
│              │  initialized       │            │
│ list_tools() │ ─ tools/list ────► │            │
│ call_tool()  │ ─ tools/call ────► │            │
│ close()      │                    └────────────┘
└──────────────┘
```

**Key points**

- This is the **MCP handshake**: `initialize` → `notifications/initialized`
  → then requests. Both of us must be able to explain it at the review.
- One event loop in a background thread holds the session open. Each sync
  method does `run_coroutine_threadsafe(...).result()`.
- Errors raise `McpClientError` (one exception per module).
- `close()` must stop the server process (no zombies).

---

## Step 3 — Tools in the sandbox: `mcp/tools.py`

Turn the client into the mapping `Sandbox` already takes:

```python
tools = {t.name: make_caller(client, t.name) for t in client.list_tools()}
with Sandbox(config, tools) as sbx: ...
```

**Key points**

- A tool result is a list of content blocks. Join the text blocks into
  one string.
- If the result has `isError`, **raise**. `_call_tool` then sends
  `ok=False` and the LLM sees a `ToolError`.
- A tool named `final_answer` must not replace ours. Skip it and warn.

---

## Step 4 — The sandbox manual: `mcp/manual.py`

Turn each schema into one short entry for the system prompt.

```text
 {"name": "run_tests",                    - run_tests(code: str,
  "inputSchema": {"properties": {   ──►       test_list: list[str]) -> str
    "code": {"type": "string"}, ...}}}      Run code against test assertions.
```

```text
"string" → str    "integer" → int    "number" → float    "boolean" → bool
"array"  → list[<items>]    "object" → dict    not required → "= None"
```

**Key points**

- `prompt.py` keeps the fixed text (format, rules, example). The tool list
  becomes a `{manual}` slot. `final_answer` is always added by us.
- The manual and `Sandbox(tools=...)` come from the **same** `list_tools()`
  call, so they can't disagree.
- **Token budget**: the system prompt is re-sent at every step (6,000 input
  tokens in total). If a server has many tools, list names + one line, and
  add a `help_tool(name)` built-in for the details.
- Fix the example in `prompt.py`: it calls `run_tests` with positional
  arguments, which the stubs reject today.

---

## Step 5 — Wire it into the agent

`agent_mbpp` only has the 4 subject flags. So it starts
`python mcp_tools_mbpp.py` over stdio itself, builds the manual, then runs
the loop.

```text
 agent_mbpp ──► McpClient(stdio) ──► list_tools()
                    │                    ├─► manual  → system prompt
                    │                    └─► tools   → Sandbox(tools=...)
                    └─► close() at the end (even on error)
```

---

## Step 6 — Streamable HTTP

Add the second transport to `McpClient` (`connect_http(url)`), and an HTTP
mode to our server (for example `python mcp_tools_mbpp.py --http`).

**Key points**

- Only the connect part changes. `list_tools` / `call_tool` stay the same.
- Same tests as stdio, run on both transports.

---

## Step 7 — Resources and prompts

Discover them with `resources/list` and `prompts/list`. Expose them as
built-ins next to `final_answer`, and list them in the manual.

```text
list_resources()        → names + URIs
read_resource(uri)      → text
get_prompt(name, **kw)  → text
```

---

## Step 8 — The sandbox CLI

```sh
uv run sandbox                                          # REPL, no tools
uv run sandbox --mcp-stdio "python mcp_tools_mbpp.py" sandbox_template.json
uv run sandbox --mcp-server <URL>
```

A REPL: read code, run it in the sandbox with the MCP tools and
`final_answer`, print the result, exit on `exit` or Ctrl+D.

---

## Step 9 — Test with an unknown server

Write a tiny **test-only** server in `tests/` with other tools (other names,
types, optional args). Check that discovery, the manual and the calls work
without changing any code.

---

## Later: SWE-bench

`mcp_tools_swebench.py` with the 9 mandatory tools, reading `TESTBED_PATH`.
Same client, same manual: only the server is new.
