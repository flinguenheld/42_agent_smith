"""
src/agent_smith/sandbox/
├── __init__.py      # exports: execute, Sandbox, SandboxConfig, ExecResult
├── config.py        # SandboxConfig (Pydantic, the subject's exact fields) + from_json()
├── result.py        # ExecResult, Status, to_observation()
├── policy.py        # PURE functions: AST check, safe builtins, import hook, safe open, audit hook
├── protocol.py      # JSON-lines messages between parent and worker (no pickle)
├── worker.py        # child entry point: python -I -m agent_smith.sandbox.worker
├── host.py          # parent side: start, kill, restart the worker; deadline; tool relay
└── api.py           # execute() + Sandbox (persistent session for the REPL)
"""

from .config import SandboxConfig, SandboxConfigError
from .host import Sandbox, execute
from .result import ExecResult, Status

__all__ = [
    "ExecResult",
    "Sandbox",
    "SandboxConfig",
    "SandboxConfigError",
    "Status",
    "execute",
    "run",
]
