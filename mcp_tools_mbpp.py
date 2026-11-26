"""Excuse for an MCP server"""

from mcp.server.fastmcp import FastMCP

from agent_smith.tools.mbpp import run_tests

server = FastMCP("mbpp-mcp-server")
server.tool()(run_tests)

if __name__ == "__main__":
    server.run()
