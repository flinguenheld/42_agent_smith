"""MCP server for MBPP. The subject wants this file at the repo root.

Run: uv run python mcp_tools_mbpp.py   (stdio)
The code lives in src/agent_smith/mcp_servers/mbpp.py.
"""

from agent_smith.mcp_servers.mbpp import server

if __name__ == "__main__":
    server.run()  # stdio by default; HTTP comes in a later step
