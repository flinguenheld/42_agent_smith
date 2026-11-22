"""Colored messages shared by every package of the project.

Warning for MCP servers in stdio mode: stdout carries the MCP protocol,
so use only print_error (stderr) there, never print_info (stdout).
"""

import sys

from termcolor import colored

from agent_smith.data import DEBUG


def print_error(title: str, message: str) -> None:
    """Print an error in red on stderr."""
    header = f"--- {title} ERROR ---\n"
    footer = "-" * (len(header) - 1)

    print(colored(header, "red"), file=sys.stderr)
    for line in message.splitlines():
        print(colored(f"   {line}", "red"), file=sys.stderr)
    print(colored(f"{footer}", "red"), file=sys.stderr)


def print_info(message: str) -> None:
    """Print an information message in green on stdout."""
    print(colored(message, "green"))


def print_debug(message: str | None, title: str = "Debug") -> None:
    """Print message in purple if DEBUG is true."""

    if DEBUG and message:
        prefix = f"     {title}  -> "
        blank = " " * len(prefix)
        first, *rest = message.splitlines()

        print(colored(prefix + first, "magenta"))
        for line in rest:
            print(colored(blank + line, "magenta"))
        print()
