from enum import Enum

from agent_smith.agent.budget import TokenBudget
from agent_smith.agent.deadline import Deadline
from agent_smith.agent.extract import extract_code
from agent_smith.agent.prompt import (
    NO_CODE_MESSAGE,
    build_task_message,
)
from agent_smith.agent.report import Report
from agent_smith.data import MAX_ITERATIONS
from agent_smith.display import Display
from agent_smith.llm.client import LLMClient, LLMClientError, LLMResponse
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

    solve()
     └─ _loop()   until: final answer, max iterations,
         │               token budget, timeout or API error
         └─ _step()
             ├─ _think()           ask the LLM    → messages
             ├─ extract_code()
             ├─ no code: _ask_for_code()  ask again → messages, report
             └─ code:    _observe()       run code  → messages, report
    """

    def __init__(
        self,
        client: LLMClient,
        sandbox: Sandbox,
        task: MBPPTaskInput,
        system_prompt: str,
        max_iterations: int = MAX_ITERATIONS,
    ) -> None:
        self.client = client
        self.sandbox = sandbox
        self.task = task
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations
        self.iteration = 0
        self.messages: list[dict[str, str]] = []
        self.budget = TokenBudget()
        self.deadline = Deadline()
        self.report = self._new_report()

    # -------------------------------------------------------------- SOLVE ----
    def solve(self) -> SolutionOutput:
        """Run the task and return its SolutionOutput."""

        self.deadline = Deadline()
        self.messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": build_task_message(self.task)},
        ]
        self.budget = TokenBudget()
        self.iteration = 0
        self.report = self._new_report()

        answer, error = self._loop()
        return self.report.build(
            self.task.task_id, answer, error, self.deadline.elapsed
        )

    def _new_report(self) -> Report:
        """Return an empty Report for the client's endpoint."""

        config = self.client.config
        return Report(config.url, config.model_name, self.system_prompt)

    # --------------------------------------------------------------- LOOP ----
    def _loop(self) -> tuple[str | None, str | None]:
        """Run steps until a final answer, a limit or an API error.

        Return (final answer, error); exactly one of them is None.
        """

        try:
            for _ in range(self.max_iterations):
                if not self.budget.has_room:
                    return None, StopReason.TOKEN_BUDGET.value
                if self.deadline.expired:
                    return None, StopReason.TIMEOUT.value

                self.iteration += 1  # only steps that really run
                answer = self._step()
                if answer is not None:
                    return answer, None

        except LLMClientError as err:
            return None, f"{StopReason.API_ERROR.value}: {err}"

        return None, StopReason.MAX_ITERATIONS.value

    # --------------------------------------------------------------- STEP ----
    def _step(self) -> str | None:
        """Think, extract, observe. Return the final answer, or None."""

        response = self._think()
        code = extract_code(response.text)

        if code is None:
            self._ask_for_code(response)
            return None

        return self._observe(response, code)

    # ------------------------------------- THINK ----
    def _think(self) -> LLMResponse:
        """Send the conversation to the LLM and count its tokens."""

        response = self.client.ask(
            self.messages,
            self.budget.max_tokens_for_next_call,
            self.deadline.remaining,
        )
        self.budget.add(response.input_tokens, response.output_tokens)
        self._add_message("assistant", response.text)
        return response

    # ------------------------------ ASK FOR CODE ----
    def _ask_for_code(self, response: LLMResponse) -> None:
        """Ask the LLM again for a python block."""

        self._add_message("user", NO_CODE_MESSAGE)
        self._record_step(response, "", "")

    # ----------------------------------- OBSERVE ----
    def _observe(self, response: LLMResponse, code: str) -> str | None:
        """Run the code and send the observation back to the LLM."""

        result = self.sandbox.run(code)
        observation = result.to_observation()
        self._add_message("user", "Observation: " + observation)
        self._record_step(response, code, observation)
        return result.final_answer

    # ------------------------------ RECORD / ADD ----
    def _record_step(
        self, response: LLMResponse, code: str, observation: str
    ) -> None:
        """Save the step in the report and show it in debug mode."""

        step = self.report.add_step(response, code, observation)
        Display.debug(step, f"Step {step.step}")

    def _add_message(self, role: str, content: str) -> None:
        """Append one message to the conversation."""

        self.messages.append({"role": role, "content": content})
