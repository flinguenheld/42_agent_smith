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
    stdout: str
    stderr: str
    error: str | None
    final_answer: str | None
    truncated: bool
    namespace_reset: bool
    duration_s: float

    def to_observation(self) -> str:
        """
        Explicit text formatting exit status for prompt injection
        """
        pass
