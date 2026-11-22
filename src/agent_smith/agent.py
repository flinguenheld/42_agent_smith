from enum import Enum

from agent_smith.budget import TokenBudget
from agent_smith.data import BENCHMARK, MAX_ITERATIONS
from agent_smith.deadline import Deadline
from agent_smith.extract import extract_code
from agent_smith.llm_client import LLMClient, LLMClientError, LLMResponse
from agent_smith.models import MBPPTaskInput, SolutionOutput, StepMetrics
from agent_smith.prompt import (
    NO_CODE_MESSAGE,
    SYSTEM_PROMPT,
    build_task_message,
)
from agent_smith.sandbox import Sandbox


class StopReason(str, Enum):
    """Why the agent stopped without a final answer."""

    API_ERROR = "API error"
    MAX_ITERATIONS = "max iterations reached"
    TIMEOUT = "timeout"
    TOKEN_BUDGET = "token budget exhausted"


class Agent:
    """Solve one MBPP task: ask the LLM, run its code, show the result.

    The caller creates (and closes) the client and the sandbox.
    """

    def __init__(
        self,
        client: LLMClient,
        sandbox: Sandbox,
        task: MBPPTaskInput,
        max_iterations: int = MAX_ITERATIONS,
    ) -> None:
        self.client = client
        self.sandbox = sandbox
        self.task = task
        self.max_iterations = max_iterations
        self.messages: list[dict[str, str]] = []
        self.budget = TokenBudget()
        self.deadline = Deadline()
        self.steps: list[StepMetrics] = []

    # -------------------------------------------------------------- SOLVE ----
    def solve(self) -> SolutionOutput:
        """Run the task and return its SolutionOutput."""

        self.deadline = Deadline()
        self.messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_task_message(self.task)},
        ]
        self.budget = TokenBudget()
        self.steps = []

        answer, error = self._loop()
        return self._build_output(answer, error, self.deadline.elapsed)

    # --------------------------------------------------------------- LOOP ----
    def _loop(self) -> tuple[str | None, str | None]:
        """Run rounds until a final answer, a limit or an API error.

        Return (final answer, error); exactly one of them is None.
        """

        try:
            for _ in range(self.max_iterations):
                if not self.budget.has_room:
                    return None, StopReason.TOKEN_BUDGET.value
                if self.deadline.expired:
                    return None, StopReason.TIMEOUT.value

                answer = self._round()
                if answer is not None:
                    return answer, None

        except LLMClientError as err:
            return None, f"{StopReason.API_ERROR.value}: {err}"

        return None, StopReason.MAX_ITERATIONS.value

    # -------------------------------------------------------------- ROUND ----
    def _round(self) -> str | None:
        """Ask, extract, run. Return the final answer, or None."""

        response = self.client.ask(
            self.messages,
            self.budget.max_tokens_for_next_call,
            self.deadline.remaining,
        )
        self.budget.add(response.input_tokens, response.output_tokens)
        self._add("assistant", response.text)

        code = extract_code(response.text)
        if code is None:
            self._add("user", NO_CODE_MESSAGE)
            self._record(response, "", "")
            return None

        result = self.sandbox.run(code)
        observation = result.to_observation()
        self._add("user", "Observation: " + observation)
        self._record(response, code, observation)
        return result.final_answer

    def _add(self, role: str, content: str) -> None:
        """Append one message to the conversation."""

        self.messages.append({"role": role, "content": content})

    # ------------------------------------------------------------ METRICS ----
    def _record(
        self, response: LLMResponse, code: str, observation: str
    ) -> None:
        """Save the StepMetrics of one round ("" when nothing was run)."""

        self.steps.append(
            StepMetrics(
                step=len(self.steps) + 1,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                request_time_ms=response.request_time_ms,
                api_url=self.client.config.url,
                model_name=self.client.config.model_name,
                llm_output=response.text,
                sandbox_input=code,
                sandbox_output=observation,
                retries=response.retries,
            )
        )

    def _build_output(
        self, answer: str | None, error: str | None, seconds: float
    ) -> SolutionOutput:
        """Gather the steps and totals into the subject's output model."""

        return SolutionOutput(
            task_id=str(self.task.task_id),
            benchmark=BENCHMARK,
            success=answer is not None,
            solution=answer or "",
            iterations=len(self.steps),
            total_requests=sum(s.retries + 1 for s in self.steps),
            total_input_tokens=sum(s.input_tokens for s in self.steps),
            total_output_tokens=sum(s.output_tokens for s in self.steps),
            total_time_seconds=seconds,
            steps=self.steps,
            system_prompt=SYSTEM_PROMPT,
            error=error,
        )
