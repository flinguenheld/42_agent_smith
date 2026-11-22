import time

from agent_smith.data import TIMEOUT_SECONDS


class Deadline:
    """Wall-clock time limit of one task; the clock starts at creation."""

    def __init__(self, seconds: float = TIMEOUT_SECONDS) -> None:
        self.seconds = seconds
        self.start = time.perf_counter()

    @property
    def elapsed(self) -> float:
        """Return the seconds since the start."""

        return time.perf_counter() - self.start

    @property
    def remaining(self) -> float:
        """Return the seconds left before the limit (0 when expired)."""

        return max(0.0, self.seconds - self.elapsed)

    @property
    def expired(self) -> bool:
        """Return True when no time is left."""

        return self.remaining == 0.0
