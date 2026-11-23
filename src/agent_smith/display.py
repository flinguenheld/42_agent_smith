import sys

from pydantic import BaseModel
from termcolor import colored

from agent_smith.data import DEBUG_LEVEL, DebugLevel


class Display:
    """Helpers to print with colors and debug levels."""

    # -------------------------------------------------------------- ERROR ----
    @staticmethod
    def error(title: str, message: str) -> None:
        """Print an error in red on stderr."""
        header = f"--- {title} ERROR ---\n"
        footer = "-" * (len(header) - 1)

        print(colored(header, "red"), file=sys.stderr)
        for line in message.splitlines():
            print(colored(f"   {line}", "red"), file=sys.stderr)
        print(colored(f"{footer}", "red"), file=sys.stderr)

    # --------------------------------------------------------------- INFO ----
    @staticmethod
    def info(message: str) -> None:
        """Print an information message in green on stdout."""
        print(colored(message, "green"))

    # -------------------------------------------------------------- DEBUG ----
    @staticmethod
    def debug(
        message: str | BaseModel | None,
        title: str = "Debug",
        level: DebugLevel = DebugLevel.SUMMARY,
    ) -> None:
        """Print message in purple on stderr if level <= DEBUG_LEVEL.

        A model is shown as its summary, or as full JSON at FULL level.
        """

        if level > DEBUG_LEVEL or not message:
            return

        text = Display._to_text(message)
        prefix = f"     {title}  -> "
        blank = " " * len(prefix)
        first, *rest = text.splitlines()

        print(colored(prefix + first, "magenta"), file=sys.stderr)
        for line in rest:
            print(colored(blank + line, "magenta"), file=sys.stderr)
        print(file=sys.stderr)

    @staticmethod
    def _to_text(message: str | BaseModel) -> str:
        """Return message as text: a model's summary, or its full JSON."""

        if isinstance(message, str):
            return message
        if DEBUG_LEVEL >= DebugLevel.FULL:
            return message.model_dump_json(indent=2)
        return str(message)
