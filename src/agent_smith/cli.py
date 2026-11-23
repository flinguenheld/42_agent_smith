from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

from agent_smith.data import DebugLevel
from agent_smith.display import Display


class _Parser(argparse.ArgumentParser):
    """Make the error beautiful again."""

    def error(self, message: str) -> NoReturn:
        """Print the error and the full help in a red block, then exit 2."""

        text = f"{message}\n\n------\n{self.format_help()}"
        Display.error("ARGUMENTS", text)
        sys.exit(2)


@dataclass
class CliArgs:
    """The command line options: the moulinette's 4, plus --debug."""

    task_file: Path
    output: Path
    model_name: str
    provider_url: str
    debug: DebugLevel

    # -------------------------------------------------------------- PARSE ----
    @classmethod
    def parse(cls, prog: str, argv: list[str] | None = None) -> CliArgs:
        """Read the command line and return typed arguments.

        argv: None reads sys.argv; a test can pass its own list.
        """

        parser = cls._build_parser(prog)
        ns = parser.parse_args(argv)
        cls._check_paths(parser, ns)
        debug = DebugLevel[ns.debug.upper()]  # "steps" → DebugLevel.STEPS

        return cls(
            ns.task_file, ns.output, ns.model_name, ns.provider_url, debug
        )

    # ------------------------------------------------------- BUILD PARSER ----
    @staticmethod
    def _build_parser(prog: str) -> argparse.ArgumentParser:
        """Return the parser for all the options."""

        parser = _Parser(prog=prog)
        parser.add_argument(
            "--task-file",
            type=Path,
            metavar="FILE",
            required=True,
            help="task JSON dumped by the moulinette",
        )
        parser.add_argument(
            "--output",
            type=Path,
            metavar="FILE",
            required=True,
            help="where to write solution.json",
        )
        parser.add_argument(
            "--model-name",
            metavar="NAME",
            required=True,
            help='e.g. "llama-3.3-70b"',
        )
        parser.add_argument(
            "--provider-url",
            metavar="URL",
            required=True,
            help='base URL, e.g. "https://api.groq.com/openai/v1"',
        )
        parser.add_argument(
            "--debug",
            metavar="LEVEL",
            choices=[level.name.lower() for level in DebugLevel],
            default=DebugLevel.OFF.name.lower(),
            help=", ".join(level.name.lower() for level in DebugLevel),
        )
        return parser

    # -------------------------------------------------------- CHECK PATHS ----
    @staticmethod
    def _check_paths(
        parser: argparse.ArgumentParser, ns: argparse.Namespace
    ) -> None:
        """Stop early (usage + exit 2) if a path is wrong, before the run."""

        if not ns.task_file.is_file():
            parser.error(f"--task-file: '{ns.task_file}' is not a file")
        if not ns.output.parent.is_dir():
            parser.error(
                f"--output: folder '{ns.output.parent}' does not exist"
            )
