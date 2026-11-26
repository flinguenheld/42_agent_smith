"""Entry point of `uv run sandbox`: the interactive sandbox (REPL)."""

from __future__ import annotations

import signal
import sys
from types import FrameType

from agent_smith.sandbox.config import SandboxConfig
from agent_smith.sandbox.host import Sandbox
from agent_smith.sandbox.repl import run_repl


def _exit_on_sigterm(signum: int, frame: FrameType | None) -> None:
    """SIGTERM -> SystemExit, so `with Sandbox()` still closes the worker."""
    sys.exit(128 + signum)

def _enable_line_editing() -> None:
    """Arrow keys and history for input(), where readline exists."""
    try:
        import readline
    except ImportError:
        pass # not on this system, plain input() still works

def main() -> int:
    """Run the interactive sandbox; return the process exit code."""
    signal.signal(signal.SIGTERM, _exit_on_sigterm)
    _enable_line_editing()
    with Sandbox(SandboxConfig()) as sbx:
        return run_repl(sbx)
