"""Colored messages shared by every package of the project.

Warning for MCP servers in stdio mode: stdout carries the MCP protocol,
so use only print_error (stderr) there, never print_info (stdout).
"""

import sys

from termcolor import colored


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
