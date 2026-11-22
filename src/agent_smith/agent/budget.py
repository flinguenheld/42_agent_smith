from agent_smith.data import (
    MAX_INPUT_TOKENS,
    MAX_OUTPUT_TOKENS,
    MAX_TOKENS_PER_CALL,
)


class TokenBudget:
    """Token limits of one task, and what was used so far."""

    def __init__(
        self,
        max_input: int = MAX_INPUT_TOKENS,
        max_output: int = MAX_OUTPUT_TOKENS,
    ) -> None:
        self.max_input = max_input
        self.max_output = max_output
        self.input_used = 0
        self.output_used = 0
        self.last_call_input = 0

    # ---------------------------------------------------------------- ADD ----
    def add(self, input_tokens: int, output_tokens: int) -> None:
        """Record the tokens of one API call."""

        self.input_used += input_tokens
        self.output_used += output_tokens
        self.last_call_input = input_tokens

    # ----------------------------------------------------------- HAS ROOM ----
    @property
    def has_room(self) -> bool:
        """Return True if the next call fits in both limits.

        The history only grows, so the next call costs at least as many
        input tokens as the last one.
        """

        next_input = self.input_used + self.last_call_input
        return (
            next_input <= self.max_input and self.output_used < self.max_output
        )

    # ----------------------------------------------------- MAX TOKEN NEXT ----
    @property
    def max_tokens_for_next_call(self) -> int:
        """Return the max_tokens to send: the output left, capped."""

        return min(MAX_TOKENS_PER_CALL, self.max_output - self.output_used)
