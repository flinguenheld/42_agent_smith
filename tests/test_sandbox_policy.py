"""Sandbox policy tests: pure functions first, then real runs."""

import ast

import pytest

from agent_smith.sandbox import SandboxConfig, Status, execute
from agent_smith.sandbox.policy import (
    check_ast,
    check_import,
    is_import_allowed,
)

ALLOW = ["math", "collections", "collections.*", "json", "typing.*"]


@pytest.fixture
def cfg(tmp_path):
    testbed, agent = tmp_path / "testbed", tmp_path / "agent"
    testbed.mkdir()
    agent.mkdir()
    return SandboxConfig(
        allowed_directories=[str(testbed), str(agent)],
        max_execution_time_seconds=5,
    )


def run(code, cfg):
    return execute(code, cfg)


# ------------------------------------------------- step 0: still works


@pytest.mark.parametrize(
    "code, expected",
    [
        ("print('hi')", "hi"),
        ("1 + 1", "2"),
        ("def f():\n    return 1 / 0\nf()", "ZeroDivisionError"),
    ],
)
def test_basic_behaviour_unchanged(cfg, code, expected):
    assert expected in run(code, cfg).to_observation()


# ------------------------------------------- step 1: pure import rules


@pytest.mark.parametrize(
    "name, allowed",
    [
        ("math", True),
        ("collections", True),
        ("collections.abc", True),  # via collections.*
        ("typing.io", True),  # via typing.*
        ("typing", False),  # typing.* does NOT allow typing
        ("os", False),
        ("mathx", False),  # exact match, not a prefix
        ("json.decoder", False),  # json allowed, json.* not
    ],
)
def test_is_import_allowed(name, allowed):
    assert is_import_allowed(name, ALLOW) is allowed


@pytest.mark.parametrize(
    "name, fromlist, level, ok",
    [
        ("math", (), 0, True),
        ("collections.abc", (), 0, True),
        ("collections", ("abc",), 0, True),
        ("typing.io", (), 0, False),  # would bind `typing`
        ("typing.io", ("IO",), 0, True),  # from typing.io import IO
        ("os", (), 0, False),
        ("", ("x",), 1, False),  # from . import x
        ("math", ("*",), 0, False),  # from math import *
    ],
)
def test_check_import(name, fromlist, level, ok):
    assert (check_import(name, fromlist, level, ALLOW) is None) is ok


def test_check_ast_reports_line_numbers():
    tree = ast.parse("import math\nimport os\nfrom . import x\n")
    problems = check_ast(tree, ALLOW)
    assert len(problems) == 2
    assert problems[0].startswith("line 2:")
    assert problems[1].startswith("line 3:")


# --------------------------------------------- step 1: real sandbox runs


@pytest.mark.parametrize(
    "code",
    [
        "import os",
        "import math, os",
        "from os import path",
        "from . import x",
        "from math import *",
        "import subprocess",
        "import socket",
    ],
)
def test_import_blocked_statically(cfg, code):
    result = run(code, cfg)
    assert result.status is Status.POLICY_VIOLATION
    assert "before execution" in result.error


@pytest.mark.parametrize(
    "code",
    [
        "__import__('os')",
        "f = __import__\nf('o' + 's')",
        "def g():\n    import os\ng()",  # caught statically too: fine
    ],
)
def test_import_blocked(cfg, code):
    assert run(code, cfg).status is Status.POLICY_VIOLATION


def test_runtime_block_is_an_import_error(cfg):
    code = (
        "try:\n"
        "    __import__('numpy')\n"
        "except ImportError as e:\n"
        "    print('caught:', e)\n"
    )
    result = run(code, cfg)
    assert result.status is Status.OK
    assert "caught: import of 'numpy' is not allowed" in result.stdout


@pytest.mark.parametrize(
    "code, expected",
    [
        ("import math\nmath.sqrt(16)", "4.0"),
        ("from collections import abc\nabc.Mapping.__name__", "Mapping"),
        ("import collections.abc\ncollections.abc.Set.__name__", "Set"),
        ("import json\njson.dumps([1])", "'[1]'"),
        # allowed modules still import what they need internally
        ("import random\nrandom.seed(1)\nrandom.randint(1, 1)", "1"),
    ],
)
def test_allowed_imports_work(cfg, code, expected):
    result = run(code, cfg)
    assert result.status is Status.OK, result.to_observation()
    assert expected in result.stdout
