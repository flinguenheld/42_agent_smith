"""MCP server for MBPP: the run_tests tool.

Never print() here: over stdio, stdout carries the JSON-RPC messages.
"""

import json

from mcp.server.mcpserver import MCPServer

from agent_smith.sandbox import ExecResult, Sandbox

# Named "server", not "mcp": "mcp" is already the SDK's package name.
server = MCPServer("mbpp")


def _test_line(test: str, result: ExecResult) -> str:
    """One report line: PASS, or FAIL with the error."""
    if result.ok:
        return f"PASS: {test}"
    return f"FAIL: {test}\n{result.to_observation()}"


@server.tool()
def run_tests(code: str, test_list: list[str]) -> str:
    """Run a candidate solution against test assertions.

    Returns a JSON string: {"success": bool, "output": str}.
    success is true only if the code runs and every assertion passes.
    """
    # The code is untrusted: it runs in our own sandbox, with its limits.
    # One Sandbox for all runs: the tests see the functions defined by
    # code, and each test gets its own PASS / FAIL line.
    with Sandbox() as sbx:
        setup = sbx.run(code)
        if not setup.ok:
            output = f"The code failed:\n{setup.to_observation()}"
            return json.dumps({"success": False, "output": output})
        results = [sbx.run(test) for test in test_list]
    lines = [_test_line(t, r) for t, r in zip(test_list, results)]
    success = all(r.ok for r in results)
    return json.dumps({"success": success, "output": "\n".join(lines)})
