"""McpClient: a sync client for one MCP server over stdio.

Each call opens its own session: start the server, handshake, one
request, stop the server. Slower (~0.7 s per call) but simple: no
thread, no close(), no process left behind.
"""

from __future__ import annotations

import asyncio
import shlex
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from mcp import Client, StdioServerParameters
from mcp.types import TextContent, Tool

from agent_smith.data import MCP_CALL_TIMEOUT_S

T = TypeVar("T")


class McpClientError(Exception):
    """Raised when the server can't be reached or a call fails."""


class McpClient:
    """Sync client for one MCP server started over stdio.

    mcp = McpClient("python mcp_tools_mbpp.py")
    tools = mcp.list_tools()
    text = mcp.call_tool("run_tests", {"code": ..., "test_list": ...})
    """

    def __init__(self, command: str) -> None:
        name, *args = shlex.split(command)
        self._params = StdioServerParameters(command=name, args=args)

    def list_tools(self) -> list[Tool]:
        """Tools offered by the server (name, description, schema)."""
        return self._run(lambda client: client.list_tools()).tools

    def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Call a tool; return its text blocks joined.

        Raises McpClientError if the server marks the result is_error.
        """
        result = self._run(lambda client: client.call_tool(name, arguments))
        text = "\n".join(
            block.text
            for block in result.content
            if isinstance(block, TextContent)
        )
        if result.is_error:
            raise McpClientError(text or f"{name}() failed")
        return text

    def tool_handlers(
        self, tools: list[Tool]
    ) -> dict[str, Callable[..., str]]:
        """One sync function per tool, for Sandbox(tools=...).

        Takes the list_tools() result, not a new call: the manual and
        the sandbox must come from the same list.
        """
        return {
            tool.name: self._handler(tool.name)
            for tool in tools
            # final_answer is the sandbox's built-in, never a server tool
            if tool.name != "final_answer"
        }

    def _handler(self, name: str) -> Callable[..., str]:
        """A function that forwards its keyword arguments to tool name."""

        # A separate method, not a lambda in the loop above: each handler
        # must keep its own name (a lambda would see the last one).
        def handler(**kwargs: Any) -> str:
            return self.call_tool(name, kwargs)

        return handler

    def _run(self, request: Callable[[Client], Awaitable[T]]) -> T:
        """One session: start the server, run request, stop the server."""

        async def one_session() -> T:
            # Entering "async with" starts the server and does the
            # handshake; leaving it stops the server.
            async with Client(self._params) as client:
                return await request(client)

        try:
            return asyncio.run(
                asyncio.wait_for(one_session(), MCP_CALL_TIMEOUT_S)
            )
        except Exception as exc:
            raise McpClientError(f"MCP call failed: {exc}") from exc
