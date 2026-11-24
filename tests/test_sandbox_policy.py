"""Sandbox policy tests: pure functions first, then real runs."""

import ast
import builtins

import pytest

from agent_smith.data import BLOCKED_BUILTINS, HIDDEN_BUILTINS
from agent_smith.sandbox import SandboxConfig, Status, execute
from agent_smith.sandbox.policy import (
    ForbiddenOperation,
    check_ast,
    check_import,
    is_attr_allowed,
    is_import_allowed,
    safe_builtins,
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


# ------------------------------------------------ step 2: pure helpers


@pytest.mark.parametrize(
    "name, allowed",
    [
        ("append", True),
        ("_private", True),  # self._x must keep working
        ("__init__", True),  # super().__init__()
        ("__name__", True),
        ("__doc__", True),
        ("__class__", False),
        ("__globals__", False),
        ("__subclasses__", False),
        ("gi_frame", False),
        ("f_globals", False),
        ("tb_frame", False),
        ("____", True),  # 4 underscores: not a dunder
    ],
)
def test_is_attr_allowed(name, allowed):
    assert is_attr_allowed(name) is allowed


def test_safe_builtins_content():
    safe = safe_builtins(SandboxConfig())
    for name in BLOCKED_BUILTINS:
        with pytest.raises(ForbiddenOperation):
            safe[name]()
    for name in HIDDEN_BUILTINS:
        assert name not in safe
    assert safe["len"] is len  # harmless builtins are the real ones
    assert "__build_class__" in safe  # needed by every class statement
    assert safe["getattr"] is not getattr


def test_safe_builtins_leaves_real_builtins_alone():
    safe_builtins(SandboxConfig())
    assert builtins.eval("1") == 1  # the real module is not modified
    assert builtins.getattr("x", "upper")() == "X"


# --------------------------------------------- step 2: real sandbox runs


@pytest.mark.parametrize(
    "code",
    [
        "eval('1')",
        "exec('x = 1')",
        "compile('1', '<s>', 'eval')",
        "globals()",
        "locals()",
        "vars()",
        "input()",
        "breakpoint()",
        "help()",
        "exit()",
        "quit()",
    ],
)
def test_blocked_builtins(cfg, code):
    result = run(code, cfg)
    assert result.status is Status.POLICY_VIOLATION
    assert "is not available in the sandbox" in result.error


@pytest.mark.parametrize(
    "code", ["__loader__", "__spec__", "copyright", "credits", "license"]
)
def test_hidden_builtins(cfg, code):
    result = run(code, cfg)
    assert result.status is Status.ERROR
    assert "NameError" in result.error


@pytest.mark.parametrize(
    "code",
    [
        "getattr((), '__class__')",
        "getattr((), '__cla' + 'ss__')",  # name built at runtime
        "setattr(object(), '__class__', int)",
        "delattr(type('A', (), {}), '__dict__')",
        "g = (x for x in [1])\ngetattr(g, 'gi_frame')",
    ],
)
def test_attribute_builtins_blocked(cfg, code):
    assert run(code, cfg).status is Status.POLICY_VIOLATION


@pytest.mark.parametrize(
    "code, expected",
    [
        ("getattr([1, 2], 'count')(1)", "1"),
        ("getattr(1, 'nope', 'dflt')", "'dflt'"),
        ("hasattr([], '__iter__')", "True"),  # hasattr is not guarded
        ("class A:\n    pass\na = A()\nsetattr(a, 'x', 3)\na.x", "3"),
        (
            "class B:\n    def __init__(self):\n        self._x = 1\nB()._x",
            "1",
        ),
        ("sorted([3, 1, 2])", "[1, 2, 3]"),
        ("len('abc'), abs(-2), max(1, 5)", "(3, 2, 5)"),
    ],
)
def test_normal_builtins_still_work(cfg, code, expected):
    result = run(code, cfg)
    assert result.status is Status.OK, result.to_observation()
    assert expected in result.stdout


def test_blocked_builtin_can_be_caught(cfg):
    code = "try:\n    eval('1')\nexcept Exception as e:\n    print('caught')"
    result = run(code, cfg)
    assert result.status is Status.OK
    assert "caught" in result.stdout


def test_getattr_non_string_name(cfg):
    result = run("getattr(1, 2)", cfg)
    assert result.status is Status.ERROR
    assert "TypeError" in result.error
