"""Sandbox security tests: module views, files, limits, audit hook."""

import ast
import os
import types

import pytest

from agent_smith.sandbox import Sandbox, SandboxConfig, Status, execute
from agent_smith.sandbox.audit import AuditHook, python_dirs
from agent_smith.sandbox.errors import ForbiddenOperation, ForbiddenPath
from agent_smith.sandbox.paths import is_path_allowed
from agent_smith.sandbox.policy import (
    check_ast,
    is_import_allowed,
    make_import,
)

DEFAULT_IMPORTS = SandboxConfig().authorized_imports


# ======================================================= step 4: modules


def test_every_reachable_module_is_allowed():
    """Property: walk each allowed module's view, recursively. No module
    outside the allowlist and no private name may ever be reachable."""
    safe_import = make_import(DEFAULT_IMPORTS)
    roots = [m for m in DEFAULT_IMPORTS if not m.endswith(".*")]
    seen = set()
    todo = [safe_import(name) for name in roots]
    while todo:
        view = todo.pop()
        if view.__name__ in seen:
            continue
        seen.add(view.__name__)
        assert is_import_allowed(view.__name__, DEFAULT_IMPORTS)
        for name, value in vars(view).items():
            if name.startswith("__") and name.endswith("__"):
                continue  # the view's own __name__, __doc__...
            assert not name.startswith("_"), f"{view.__name__}.{name}"
            if isinstance(value, types.ModuleType):
                todo.append(value)
    assert "collections.abc" in seen  # sub-modules are walked too


@pytest.mark.parametrize(
    "code",
    [
        "import random\nrandom._os",
        "import collections\ncollections._sys",
        "import typing\ntyping.sys",
        "import datetime\ndatetime.sys",
        "import re\nre.enum",
        "import json\njson.decoder",
    ],
)
def test_module_leaks_are_gone(secure_cfg, code):
    result = execute(code, secure_cfg)
    assert result.status is Status.ERROR
    assert "AttributeError" in result.error


@pytest.mark.parametrize(
    "code",
    [
        "from json import decoder",  # would be the real module
        "from typing import sys",
        "from random import _os",
    ],
)
def test_from_import_of_hidden_names(secure_cfg, code):
    assert execute(code, secure_cfg).status is Status.POLICY_VIOLATION


@pytest.mark.parametrize(
    "code",
    [
        "import operator\noperator.attrgetter('x')",
        "from operator import methodcaller\nmethodcaller('x')",
        "import string\nstring.Formatter()",
    ],
)
def test_attribute_by_string_functions_blocked(secure_cfg, code):
    result = execute(code, secure_cfg)
    assert result.status is Status.POLICY_VIOLATION
    assert "is not available in the sandbox" in result.error


@pytest.mark.parametrize(
    "code, expected",
    [
        ("import collections.abc as c\nc.Set.__name__", "'Set'"),
        ("import collections.abc\ncollections.abc.Set.__name__", "'Set'"),
        ("from collections import abc\nabc.Set.__name__", "'Set'"),
        ("import collections\ncollections.namedtuple('P', 'x')(1)", "P(x=1)"),
        ("from typing import List\nList[int]", "typing.List[int]"),
        ("import math\nimport math as m\nm is math", "True"),
        ("import math\n'sqrt' in dir(math)", "True"),
        ("import random\nrandom.seed(0)\nrandom.randint(1, 1)", "1"),
    ],
)
def test_allowed_modules_still_work(secure_cfg, code, expected):
    result = execute(code, secure_cfg)
    assert result.status is Status.OK, result.to_observation()
    assert expected in result.stdout


def test_missing_name_gives_a_clear_import_error(secure_cfg):
    result = execute("from math import nope", secure_cfg)
    assert result.status is Status.ERROR
    assert "cannot import name 'nope' from 'math'" in result.error


# ========================================================= step 5: open()


def test_is_path_allowed(workspace):
    dirs = [str(workspace / "testbed")]
    assert is_path_allowed(workspace / "testbed" / "a.txt", dirs)
    assert is_path_allowed(str(workspace / "testbed"), dirs)
    assert not is_path_allowed(workspace / "outside.txt", dirs)
    assert not is_path_allowed(workspace / "testbed2" / "x", dirs)
    assert not is_path_allowed(f"{workspace}/testbed/../outside.txt", dirs)
    assert not is_path_allowed(workspace / "testbed" / "link.txt", dirs)


@pytest.mark.parametrize(
    "code, expected",
    [
        ("open('a.txt').read()", "'hello\\n'"),  # relative: cwd = testbed
        ("with open('a.txt') as f:\n    print(f.read().strip())", "hello"),
        (
            "try:\n    open('/etc/passwd')\n"
            "except PermissionError:\n    print('caught')",
            "caught",
        ),
    ],
)
def test_open_allowed(secure_cfg, code, expected):
    result = execute(code, secure_cfg)
    assert result.status is Status.OK, result.to_observation()
    assert expected in result.stdout


def test_open_write_in_agent(secure_cfg, workspace):
    code = f"open('{workspace}/agent/o.txt', 'w').write('x')"
    assert execute(code, secure_cfg).status is Status.OK
    assert (workspace / "agent" / "o.txt").read_text() == "x"


@pytest.mark.parametrize(
    "path",
    [
        "/etc/passwd",
        "{ws}/outside.txt",
        "{ws}/testbed/../outside.txt",  # path traversal
        "{ws}/testbed/link.txt",  # symlink to outside
        "{ws}/testbed2/x",  # startswith trap
    ],
)
def test_open_denied(secure_cfg, workspace, path):
    code = f"open('{path.format(ws=workspace)}')"
    result = execute(code, secure_cfg)
    assert result.status is Status.POLICY_VIOLATION
    assert "is denied" in result.error


@pytest.mark.parametrize(
    "code", ["open(1, 'w')", "open(4, 'w')", "open('a.txt', opener=print)"]
)
def test_open_tricks_denied(secure_cfg, code):
    assert execute(code, secure_cfg).status is Status.POLICY_VIOLATION


# ======================================================= step 6: limits


@pytest.mark.parametrize(
    "code",
    [
        "x = bytearray(1024 ** 3)",
        "x = [0] * (10 ** 9)",
        "x = 'a' * (300 * 1024 ** 2)",
    ],
)
def test_memory_limit(secure_cfg, code):
    assert execute(code, secure_cfg).status is Status.MEMORY


def test_memory_under_the_limit(secure_cfg):
    result = execute("len(bytearray(50 * 1024 ** 2))", secure_cfg)
    assert result.status is Status.OK


def test_worker_survives_memory_error(secure_cfg):
    with Sandbox(secure_cfg) as sbx:
        sbx.run("keep = 41")
        assert sbx.run("x = bytearray(1024 ** 3)").status is Status.MEMORY
        after = sbx.run("keep + 1")
    assert after.status is Status.OK
    assert "42" in after.stdout


def test_file_size_limit(secure_cfg, workspace):
    code = f"open('{workspace}/agent/big', 'wb').write(b'0' * 70 * 1024**2)"
    result = execute(code, secure_cfg)
    assert result.status is Status.ERROR
    assert "File too large" in result.error


def test_open_files_limit(secure_cfg):
    result = execute("f = [open('a.txt') for _ in range(100)]", secure_cfg)
    assert result.status is Status.ERROR
    assert "Too many open files" in result.error


# ================================================ step 7: the hook alone


@pytest.fixture
def hook(workspace):
    """An AuditHook called directly: no process, no installation."""
    dirs = [str(workspace / "testbed"), str(workspace / "agent")]
    return AuditHook(dirs, lambda tree: check_ast(tree, DEFAULT_IMPORTS))


@pytest.mark.parametrize(
    "event",
    [
        "os.system",
        "os.exec",
        "os.fork",
        "os.kill",
        "subprocess.Popen",
        "socket.__new__",
        "socket.connect",
        "socket.getaddrinfo",
        "ctypes.dlopen",
        "sys.addaudithook",
        "gc.get_objects",
    ],
)
def test_hook_denies_events(hook, event):
    with pytest.raises(ForbiddenOperation):
        hook(event, ())


def test_hook_allows_other_events(hook):
    hook("import", ("json", None, [], [], []))
    hook("exec", (None,))


def test_hook_open_rules(hook, workspace):
    stdlib_file = f"{python_dirs()[0]}/json/__init__.py"
    hook("open", (str(workspace / "testbed" / "a.txt"), "r", 0))
    hook("open", (str(workspace / "agent" / "o.txt"), "w", 0))
    hook("open", (stdlib_file, "r", 0))  # the interpreter loads modules
    for path, mode in [
        ("/etc/passwd", "r"),
        (stdlib_file, "w"),  # read-only for the stdlib
        (str(workspace / "testbed" / "link.txt"), "r"),
        (4, "w"),  # the protocol pipe
    ]:
        with pytest.raises(ForbiddenPath):
            hook("open", (path, mode, 0))


def test_hook_write_detected_from_flags(hook):
    with pytest.raises(ForbiddenPath):
        hook("open", ("/tmp/x", None, os.O_WRONLY | os.O_CREAT))


def test_hook_compile_rule(hook):
    hook("compile", (b"lambda _cls, x: _tuple_new(_cls, (x,))", "<string>"))
    hook("compile", (b"int", "<string>"))
    hook("compile", (ast.parse("x.__class__"), "<string>"))  # an AST: ok
    hook("compile", (b"x.__class__", "<sandbox-3>"))  # the worker's own
    with pytest.raises(ForbiddenOperation):
        hook("compile", (b"().__class__.__base__", "<string>"))


# =================================== step 7: the hook in a real worker


@pytest.mark.parametrize(
    "code, event",
    [
        ("import socket\nsocket.socket()", "socket.__new__"),
        (
            "import socket\nsocket.create_connection(('1.1.1.1', 80))",
            "socket.getaddrinfo",
        ),
        ("import os\nos.system('echo pwned')", "os.system"),
        ("import subprocess\nsubprocess.run(['ls'])", "subprocess.Popen"),
        ("import os\nos.fork()", "os.fork"),
        ("import os\nos.kill(os.getppid(), 9)", "os.kill"),
    ],
)
def test_network_and_processes_blocked(leaky_cfg, code, event):
    result = execute(code, leaky_cfg)
    assert result.status is Status.POLICY_VIOLATION
    assert event in result.error


@pytest.mark.parametrize(
    "code",
    [
        "import os\nos.open('/etc/passwd', os.O_RDONLY)",
        "import os\nos.open('{ws}/x', os.O_WRONLY | os.O_CREAT)",
        "import os\nos.listdir('/')",
        "import os\nos.remove('{ws}/outside.txt')",
        "import shutil\nshutil.rmtree('{ws}/testbed')",
        "import os\nos.fdopen(4, 'w')",
    ],
)
def test_files_blocked_without_safe_open(leaky_cfg, workspace, code):
    result = execute(code.format(ws=workspace), leaky_cfg)
    assert result.status is Status.POLICY_VIOLATION
    assert (workspace / "outside.txt").exists()
    assert (workspace / "testbed" / "a.txt").exists()


def test_listdir_allowed_inside(leaky_cfg, workspace):
    code = f"import os\nsorted(os.listdir('{workspace}/testbed'))"
    result = execute(code, leaky_cfg)
    assert result.status is Status.OK
    assert "a.txt" in result.stdout


@pytest.mark.parametrize(
    "code",
    [
        "import typing\n"
        "def f(x: '().__class__'):\n    pass\n"
        "typing.get_type_hints(f)",
        "import functools\n"
        "@functools.singledispatch\ndef g(x):\n    pass\n"
        "@g.register\ndef _(x: '().__class__'):\n    pass",
    ],
)
def test_runtime_compile_is_checked(secure_cfg, code):
    result = execute(code, secure_cfg)
    assert result.status is Status.POLICY_VIOLATION
    assert "code compiled at runtime was rejected" in result.error


@pytest.mark.parametrize(
    "code, expected",
    [
        (
            "import typing\ndef f(x: 'int'):\n    pass\n"
            "typing.get_type_hints(f)",
            "{'x': <class 'int'>}",
        ),
        ("import collections\ncollections.namedtuple('P', 'x')(1)", "P(x=1)"),
    ],
)
def test_runtime_compile_of_safe_code(secure_cfg, code, expected):
    result = execute(code, secure_cfg)
    assert result.status is Status.OK, result.to_observation()
    assert expected in result.stdout


def test_first_import_after_lock_down(workspace, secure_cfg):
    imports = secure_cfg.authorized_imports + ["statistics", "fractions"]
    cfg = secure_cfg.model_copy(update={"authorized_imports": imports})
    code = "import statistics\nstatistics.mean([1, 2, 3])"
    result = execute(code, cfg)
    assert result.status is Status.OK, result.to_observation()
    assert "2" in result.stdout


@pytest.mark.parametrize(
    "code, expected",
    [
        ("def f():\n    return 1 / 0\nf()", "return 1 / 0"),
        ("import json\njson.loads('{')", "JSONDecodeError"),
    ],
)
def test_tracebacks_still_work(secure_cfg, code, expected):
    result = execute(code, secure_cfg)
    assert result.status is Status.ERROR
    assert expected in result.error


def test_tools_and_final_answer_after_lock_down(secure_cfg):
    tools = {"read_file": lambda path: f"content of {path}"}
    code = "final_answer(read_file(path='/x'))"
    result = execute(code, secure_cfg, tools)
    assert result.status is Status.OK
    assert result.final_answer == "content of /x"
