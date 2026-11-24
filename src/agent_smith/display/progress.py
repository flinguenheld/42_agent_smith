from collections.abc import Callable, Iterable

from rich.console import Console, RenderableType
from rich.progress import BarColumn, Progress, TaskID, TextColumn


class TaskProgress(Progress):
    """Progress bars of one task; each bar follows a live value."""

    def __init__(self, console: Console) -> None:
        # Before super(): its Live already calls get_renderables once.
        self._bars: dict[TaskID, Callable[[], float]] = {}
        super().__init__(
            TextColumn("{task.description}"),
            BarColumn(),
            TextColumn(
                "{task.completed:>5.0f} / {task.total:.0f} {task.fields[unit]}"
            ),
            console=console,
        )

    def add_bar(
        self,
        title: str,
        total: float,
        unit: str,
        value: Callable[[], float],
    ) -> None:
        """Add a bar that shows value() out of total at each refresh."""
        self._bars[self.add_task(title, total=total, unit=unit)] = value

    def get_renderables(self) -> Iterable[RenderableType]:
        """Move each bar to its current value, then draw them."""
        for task, value in self._bars.items():
            self.update(task, completed=value())
        yield from super().get_renderables()
