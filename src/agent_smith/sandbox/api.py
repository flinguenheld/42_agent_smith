from typing import Callable, Any, Mapping
from src.sandbox.config import SandboxConfig
from src.sandbox.result import ExecResult

ToolHandler = Callable[[str, dict[str, Any]], str]
# (tool_name, kwargs) -> result_text


def execute(
    code: str,
    config: SandboxConfig,
    tools: Mapping[str, ToolHanlder] | None = None,
) -> ExecResult:
    with Sandbox(config, tools) as sbx:
        return sbx.run(code)


class Sandbox:
    """
    Persistent session:
        one worker kept alive between run() calls (REPL, agent loop).
    """
    def __init__(self, config, tools=None):
        pass

    def run(self, code: str) -> ExecResult:
        pass

    def restart(self) -> None:
        pass

    def close(self) -> None:
        pass
