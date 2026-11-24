from collections.abc import Callable, Iterable

from rich.console import Console, RenderableType
from rich.progress import BarColumn, Progress, TaskID, TextColumn


class TaskProgress(Progress):
    """Progress bars of one task; the time bar follows a live clock."""

    def __init__(
        self,
        console: Console,
        max_seconds: float,
        elapsed: Callable[[], float],
    ) -> None:
        self._elapsed = elapsed
        self._time: TaskID | None = None  # Rich draws before add_task
        super().__init__(
            TextColumn("{task.description:<6}"),
            BarColumn(),
            TextColumn(
                "{task.completed:>5.0f} / {task.total:.0f} {task.fields[unit]}"
            ),
            console=console,
        )
        self._time = self.add_task("Time", total=max_seconds, unit="s")

    def get_renderables(self) -> Iterable[RenderableType]:
        """Move the time bar to the clock, then draw it (each refresh)."""
        if self._time is not None:
            self.update(self._time, completed=self._elapsed())
        yield from super().get_renderables()
