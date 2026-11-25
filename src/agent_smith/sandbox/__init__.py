"""Sandbox: runs LLM code in a separate, restricted Python process.

src/agent_smith/sandbox/
├── __init__.py   exports: execute, Sandbox, SandboxConfig, ExecResult
├── config.py     SandboxConfig (Pydantic, the subject's fields)
├── result.py     ExecResult, Status, to_observation()
├── protocol.py   JSON Lines messages between host and worker
├── host.py       parent side: start, deadline, kill, tool relay
├── worker.py     child side: runs the code through a Policy
├── policy.py     the security rules (SandboxPolicy)
├── errors.py     SandboxViolation and the Forbidden* exceptions
├── paths.py      is the path inside an allowed directory?
├── limits.py     setrlimit: memory, processes, file size
└── audit.py      audit hook: network, files, processes, compile
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
