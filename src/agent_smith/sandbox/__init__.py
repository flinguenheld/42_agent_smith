"""Sandbox: runs LLM code in a separate, restricted Python process.

src/agent_smith/sandbox/
├── __init__.py   exports: execute, Sandbox, SandboxConfig, ExecResult
├── config.py     SandboxConfig (Pydantic, the subject's fields)
├── result.py     ExecResult, Status, to_observation()
├── protocol.py   JSON Lines messages between host and worker
├── host.py       parent side: start, deadline, kill, tool relay
├── worker.py     child side: runs the code through a Policy
└── policy.py     the security rules (SandboxPolicy)
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
]
