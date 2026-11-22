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

    def solve(self) -> str | None:
        """Run rounds until final_answer() or max_iterations."""

        self.messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_task_message(self.task)},
        ]
        for _ in range(self.max_iterations):
            answer = self._round()
            if answer is not None:
                return answer
        return None

    def _round(self) -> str | None:
        """Ask, extract, run. Return the final answer, or None."""

        reply = self.client.ask(self.messages).text
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
