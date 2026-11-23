"""Pydantic models given by the subject."""

from datetime import datetime

from pydantic import BaseModel, Field


def _now() -> str:
    """Return the current time in ISO 8601 format."""

    return datetime.now().isoformat()


class MBPPTaskInput(BaseModel):
    """Input for MBPP task evaluation."""

    task_id: int
    task_definition: str
    function_definition: str
    test_imports: list[str] = Field(default_factory=list)
    test_list: list[str] = Field(default_factory=list)


class StepMetrics(BaseModel):
    """Metrics for one step: one LLM call, then one sandbox run."""

    step: int
    input_tokens: int
    output_tokens: int
    request_time_ms: float
    timestamp: str = Field(default_factory=_now)
    api_url: str = ""
    model_name: str = ""
    llm_output: str = ""
    sandbox_input: str = ""
    sandbox_output: str = ""
    retries: int = 0

    def __str__(self) -> str:
        return (
            f"tokens in/out={self.input_tokens}/{self.output_tokens}  "
            f"time={self.request_time_ms:.0f}ms  retries={self.retries}  "
            f"code={'yes' if self.sandbox_input else 'no'}"
        )


class SolutionOutput(BaseModel):
    """What the agent produces for one task (written to solution.json)."""

    task_id: str
    benchmark: str
    success: bool
    solution: str
    iterations: int
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_time_seconds: float
    steps: list[StepMetrics] = Field(default_factory=list)
    system_prompt: str = ""
    error: str | None = None
    timestamp: str = Field(default_factory=_now)

    def __str__(self) -> str:
        return (
            f"SolutionOutput:\n"
            f"success={self.success}  iterations={self.iterations}  "
            f"tokens in/out={self.total_input_tokens}/"
            f"{self.total_output_tokens}  "
            f"time={self.total_time_seconds:.1f}s  error={self.error}\n"
            f"{self.solution}"
        )
