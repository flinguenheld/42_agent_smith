from enum import Enum

from agent_smith.agent.budget import TokenBudget
from agent_smith.agent.deadline import Deadline
from agent_smith.agent.extract import extract_code
from agent_smith.agent.prompt import (
    NO_CODE_MESSAGE,
    SYSTEM_PROMPT,
    build_task_message,
)
from agent_smith.agent.report import Report
from agent_smith.data import MAX_ITERATIONS
from agent_smith.llm.client import LLMClient, LLMClientError
from agent_smith.models import MBPPTaskInput, SolutionOutput
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
        self.report = self._new_report()

    # -------------------------------------------------------------- SOLVE ----
    def solve(self) -> SolutionOutput:
        """Run the task and return its SolutionOutput."""

        self.deadline = Deadline()
        self.messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_task_message(self.task)},
        ]
        self.budget = TokenBudget()
        self.report = self._new_report()

        answer, error = self._loop()
        return self.report.build(
            self.task.task_id, answer, error, self.deadline.elapsed
        )

    def _new_report(self) -> Report:
        """Return an empty Report for the client's endpoint."""

        return Report(self.client.config.url, self.client.config.model_name)

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
            self.report.add_step(response, "", "")
            return None

        result = self.sandbox.run(code)
        observation = result.to_observation()
        self._add("user", "Observation: " + observation)
        self.report.add_step(response, code, observation)
        return result.final_answer

    def _add(self, role: str, content: str) -> None:
        """Append one message to the conversation."""

        self.messages.append({"role": role, "content": content})
