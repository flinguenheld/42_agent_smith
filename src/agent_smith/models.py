"""Pydantic models given by the subject, plus DebugView for Display."""

from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, Field

from agent_smith.data import DebugLevel


# ------------------------------------------------------------- DEBUG VIEW ----
@dataclass
class DebugView:
    """What Display prints for a model: text, code, then its output."""

    text: str
    code: str = ""
    output: str = ""  # plain text shown after the code (sandbox result)


# -------------------------------------------------------- MBPP TASK INPUT ----
class MBPPTaskInput(BaseModel):
    """Input for MBPP task evaluation."""

    task_id: int
    task_definition: str
    function_definition: str
    test_imports: list[str] = Field(default_factory=list)
    test_list: list[str] = Field(default_factory=list)


# ----------------------------------------------------------- STEP METRICS ----
class StepMetrics(BaseModel):
    """Metrics for one step: one LLM call, then one sandbox run."""

    step: int
    input_tokens: int
    output_tokens: int
    request_time_ms: float
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
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

    def debug_view(self, level: DebugLevel) -> DebugView:
        """Return the text, code and output to show at this level."""
        text = str(self)
        if level >= DebugLevel.FULL:
            text += f"\nllm_output:\n{self.llm_output}"
        return DebugView(text, self.sandbox_input, self.sandbox_output)


# -------------------------------------------------------- SOLUTION OUTPUT ----
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
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

    def __str__(self) -> str:
        return (
            f"{self.task_id}  success={self.success}  "
            f"iterations={self.iterations}  "
            f"requests={self.total_requests}\n"
            f"tokens in/out={self.total_input_tokens}/"
            f"{self.total_output_tokens}  "
            f"time={self.total_time_seconds:.1f}s  error={self.error}"
        )

    def debug_view(self, level: DebugLevel) -> DebugView:
        """Return the text and code to show at this debug level."""
        text = str(self)
        if level >= DebugLevel.FULL:
            text += f"\nsystem_prompt:\n{self.system_prompt}"
        return DebugView(text, self.solution)
