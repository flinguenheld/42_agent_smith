"""Colored messages shared by every package of the project.

Warning for MCP servers in stdio mode: stdout carries the MCP protocol,
so use only print_error (stderr) there, never print_info (stdout).
"""

import sys

from termcolor import colored


def print_error(message: str) -> None:
    """Print an error in red on stderr."""
    print(colored(f"Error: {message}", "red"), file=sys.stderr)


def print_info(message: str) -> None:
    """Print an information message in green on stdout."""
    print(colored(message, "green"))
