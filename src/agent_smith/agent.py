from agent_smith.budget import TokenBudget
from agent_smith.data import MAX_ITERATIONS
from agent_smith.extract import extract_code
from agent_smith.llm_client import LLMClient
from agent_smith.models import MBPPTaskInput
from agent_smith.prompt import (
    NO_CODE_MESSAGE,
    SYSTEM_PROMPT,
    build_task_message,
)
from agent_smith.sandbox import Sandbox


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

    def solve(self) -> str | None:
        """Run rounds until final_answer(), max_iterations or no budget."""

        self.messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_task_message(self.task)},
        ]
        self.budget = TokenBudget()
        for _ in range(self.max_iterations):
            if not self.budget.has_room:
                break
            answer = self._round()
            if answer is not None:
                return answer
        return None

    def _round(self) -> str | None:
        """Ask, extract, run. Return the final answer, or None."""

        response = self.client.ask(
            self.messages, self.budget.max_tokens_for_next_call
        )
        self.budget.add(response.input_tokens, response.output_tokens)

        reply = response.text
        self._add("assistant", reply)

        code = extract_code(reply)
        if code is None:
            self._add("user", NO_CODE_MESSAGE)
            return None

        result = self.sandbox.run(code)
        self._add("user", "Observation: " + result.to_observation())
        return result.final_answer

    def _add(self, role: str, content: str) -> None:
        """Append one message to the conversation."""

        self.messages.append({"role": role, "content": content})
