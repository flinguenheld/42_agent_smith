import sys

from pydantic import BaseModel
from termcolor import colored

from agent_smith.data import DebugLevel
from agent_smith.display.pretty import pretty_format


class Display:
    """Helpers to print with colors and debug levels."""

    level: DebugLevel = DebugLevel.OFF

    # ---------------------------------------------------- SET DEBUG LEVEL ----
    @classmethod
    def set_debug_level(cls, level: DebugLevel) -> None:
        """Change the debug level, e.g. from the --debug flag."""
        cls.level = level

    # -------------------------------------------------------------- ERROR ----
    @staticmethod
    def error(title: str, message: str) -> None:
        """Print an error in red on stderr."""
        header = f"\n--- {title} ERROR ---\n"
        footer = "-" * (len(header) - 2)

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
    @classmethod
    def debug(
        cls,
        message: str | BaseModel | None,
        title: str = "Debug",
        level: DebugLevel = DebugLevel.SUMMARY,
        full: bool = False,
    ) -> None:
        """Print message in light_cyan on stderr if level <= Display.level.

        A model is shown as its summary, or with all its fields if full is
        True or at FULL level.
        """

        if level > cls.level or not message:
            return

        text = cls._to_text(message, full)
        prefix = f"     {title}  -> "
        blank = " " * len(prefix)
        first, *rest = text.splitlines()

        print(colored(prefix + first, "light_cyan"), file=sys.stderr)
        for line in rest:
            print(colored(blank + line, "light_cyan"), file=sys.stderr)
        print(file=sys.stderr)

    @classmethod
    def _to_text(cls, message: str | BaseModel, full: bool) -> str:
        """Return message as text: a model's summary, or all its fields."""

        if isinstance(message, str):
            return message
        if full or cls.level >= DebugLevel.FULL:
            return pretty_format(message.model_dump())
        return str(message)
