"""The sandbox manual: the tool list the LLM reads in its system prompt.

Built from the server's tool schemas, so a new server gives a new manual
with no code change. final_answer is always added: it's ours.

 {"name": "run_tests",                     - run_tests(code: str,
  "input_schema": {"properties": {   ──►       test_list: list[str]) -> str
    "code": {"type": "string"}, ...}}}       Run a candidate solution...
"""

from __future__ import annotations

import inspect
from typing import Any

from mcp.types import Tool

from agent_smith.data import JSON_TO_PYTHON

HEADER = (
    "Functions you can call in your code "
    "(keyword arguments only, e.g. f(x=1)):"
)
FINAL_ANSWER_ENTRY = (
    "- final_answer(answer: str)\n"
    "  Submit your final answer and end the task."
)


def build_manual(tools: list[Tool]) -> str:
    """The manual for these tools, final_answer last."""
    entries = [_entry(tool) for tool in tools if tool.name != "final_answer"]
    return "\n".join([HEADER, *entries, FINAL_ANSWER_ENTRY])


def _entry(tool: Tool) -> str:
    """One tool: its signature line, then its description indented."""
    schema = tool.input_schema
    required = schema.get("required", [])
    params = ", ".join(
        _param(name, prop, name in required)
        for name, prop in schema.get("properties", {}).items()
    )
    # Every tool returns a str: McpClient.call_tool joins the text blocks.
    lines = [f"- {tool.name}({params}) -> str"]
    doc = inspect.cleandoc(tool.description or "")
    lines += [f"  {line}".rstrip() for line in doc.splitlines()]
    return "\n".join(lines)


def _param(name: str, prop: dict[str, Any], required: bool) -> str:
    """One parameter: "name: type", plus "= default" if optional."""
    text = f"{name}: {_type(prop)}"
    if required:
        return text
    return f"{text} = {prop.get('default')!r}"


def _type(prop: dict[str, Any]) -> str:
    """A JSON Schema type as a Python type ("Any" if unknown)."""
    if "anyOf" in prop:  # e.g. int | None
        return " | ".join(_type(option) for option in prop["anyOf"])
    kind = prop.get("type")
    if isinstance(kind, list):  # {"type": ["string", "null"]}
        return " | ".join(_type({"type": k}) for k in kind)
    if kind == "array" and "items" in prop:
        return f"list[{_type(prop['items'])}]"
    return JSON_TO_PYTHON.get(kind, "Any") if isinstance(kind, str) else "Any"
