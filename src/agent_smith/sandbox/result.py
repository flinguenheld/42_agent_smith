from dataclasses import dataclass
from enum import Enum


class Status(str, Enum):
    OK = "ok"
    ERROR = "error"
    SYNTAX_ERROR = "syntax_error"
    POLICY_VIOLATION = "policy_violation"
    TIMEOUT = "timeout"
    MEMORY = "memory_exceeded"
    CRASHED = "crashed"


@dataclass
class ExecResult:
    status: Status
    stdout: str = ""
    stderr: str = ""
    error: str | None = None
    final_answer: str | None = None
    truncated: bool = False
    namespace_reset: bool = False
    duration_s: float = 0.0

    @property
    def ok(self) -> bool:
        return self.status is Status.OK

    def to_observation(self) -> str:
        """
        Explicit text formatting exit status for prompt injection
        """
        parts = []
        if self.stdout:
            parts.append(f"[stdout]\n{self.stdout}")
        if self.stderr:
            parts.append(f"[stderr]\n{self.stderr}")
        if self.status is Status.TIMEOUT:
            parts.append(
                f"[timeout] Execution stopped after "
                f"{self.duration_s:.1f}s; output above is partial."
            )
        elif self.status is Status.MEMORY:
            parts.append("[memory] Execution stopped: memory limit exceeded")
        elif self.status is Status.CRASHED:
            parts.append("[crashed] The sandbox process died unexpectedly.")
        if self.error:
            parts.append(f"[{self.status.value}]\n{self.error}")
        if self.truncated:
            parts.append("[note] Output was truncated to fit the size limit.")
        if self.namespace_reset:
            parts.append(
                "[note] The sandbox was restarted: variables,"
                " functions and imports from previous steps are lost."
            )
        if self.final_answer is not None:
            parts.append("[final_answer] received.")
        if not parts:
            parts.append("[ok] Code ran successfully with no output.")
        return "\n".join(parts)
