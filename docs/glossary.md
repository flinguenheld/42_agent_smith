## Glossary

Short definitions of the terms used in the project, in alphabetical order.

---

### Agent

The program we write around an [LLM](#llm). It sends the task to the LLM, runs the code
the LLM writes, shows it the result and repeats until the task is solved.

---

### API

**Application Programming Interface.** A way for one program to use another. Here it
means sending an HTTP request to an LLM provider and getting its answer back.

---

### AST

**Abstract Syntax Tree.** The structure of some code as a tree of nodes, built
without running it. `ast.parse("x.__class__")` gives:

```text
Module
└─ Expr
   └─ Attribute(attr='__class__')
      └─ Name(id='x')
```

The sandbox reads this tree **before** running the LLM's code, and refuses forbidden
imports and attributes (`policy.check_ast`). See [NodeVisitor](#nodevisitor).

---

### Builtins

The names Python finds without importing anything: `len`, `print`, `open`, `eval`...
They are looked up in `globals["__builtins__"]`, so each [namespace](#namespace) can
have its own set.

The sandbox gives the LLM's code a filtered copy (`policy.safe_builtins`): `eval`,
`exec`, `globals`... raise an error, and `__import__` and `getattr` are replaced by
checked versions.

---

### Defense in depth

Several independent security layers, each one assuming the previous one can fail. In
the sandbox:

```text
1. static AST check     imports, dunders              policy.check_ast
2. filtered builtins    no eval/exec, safe getattr    policy.safe_builtins
3. module proxy         safe module attributes        (to do)
4. OS limits            memory, processes, audit      (to do)
   + separate process   can be killed, no API keys
```

---

### Dunder

**Double underscore**: a name like `__init__` or `__class__`. Python uses them for its
internals, and some of them link objects together. From any object,
`().__class__.__base__.__subclasses__()` reaches every loaded class, and
`func.__globals__` reaches all the variables of a module.

The sandbox refuses dunders, except `__init__`, `__name__` and `__doc__`
(`SAFE_DUNDERS` in `data.py`).

---

### EAFP / LBYL

- **EAFP**, *Easier to Ask Forgiveness than Permission*: try the action, catch the error
  (`try`/`except`). The usual Python style.
- **LBYL**, *Look Before You Leap*: check every condition with `if` first.

Keep the `try` block small, so it doesn't hide unrelated bugs.

---

### EOF

**End Of File.** A read returns nothing (`b""`) because nothing more will come: the
file is finished, or the other end of a [pipe](#pipe) is closed.

The worker exits on EOF (the host is gone). The host reports a crash on EOF (the worker
died).

---

### exec / eval

- `exec(code, ns)` runs statements, with the dict `ns` as globals. It returns `None`.
- `eval(expr, ns)` computes **one expression** and returns its value.

**Useful:** the only way to run a string as Python inside a running program. Keeping
`ns` between calls keeps the variables, like a REPL.

**Dangerous:** the code can do anything its [namespace](#namespace) allows, and
limiting the namespace is not a real security boundary. The worker runs the LLM's
code with `exec` after checking it; the LLM's code itself can't call them.

---

### Fail fast

Detect a problem and stop **as early as possible**, before any long or expensive work.
Example: `CliArgs._check_paths` rejects a wrong `--output` folder before the agent
spends 120 s and tokens on a run it couldn't save. See
[How a run works](how_a_run_works.md).

---

### File descriptor

A small integer a process uses to refer to an open file, [pipe](#pipe) or terminal.
Every read and write goes through one. 0, 1 and 2 are
[stdin / stdout / stderr](#stdin--stdout--stderr).

`os.dup2(a, b)` makes `b` point where `a` points: that is how redirection works.

---

### fromlist

The 4th parameter of `__import__(name, globals, locals, fromlist, level)`: the names
after `import` in `from X import a, b`. It is empty for `import X`.

```text
import collections.abc       → __import__("collections.abc")                 binds collections
from collections import abc  → __import__("collections", fromlist=("abc",))  binds abc
```

Without a fromlist, `__import__("a.b")` returns the top package `a`. The sandbox
applies the same import rule statically and at runtime (`policy.check_import`).

---

### httpx

A Python library that sends HTTP requests, such as a POST to an [LLM](#llm)
[API](#api), and reads the response. The standard library has `urllib.request` for
the same job, but its code is longer and harder to read.

```python
response = httpx.post(url, headers={"Authorization": f"Bearer {key}"}, json=body)
data = response.json()
```

---

### JSON Lines

A text format with one JSON object per line. A [pipe](#pipe) carries bytes with no
message boundaries, so the newline marks where each message ends. The host and the
worker talk this way (`sandbox/protocol.py`):

```text
{"type": "exec", "code": "print(1)"}
{"type": "output", "stream": "stdout", "data": "1\n"}
{"type": "done", "status": "ok"}
```

Unlike pickle, reading JSON can't run code.

---

### KISS

*Keep It Simple, Stupid.* Prefer the simplest solution that works. Example: we use
`argparse` (standard library, 4 flags) rather than a CLI framework.

---

### LLM

**Large Language Model.** An AI that takes text in and gives text out, such as GPT,
Claude or Llama. It can't run code by itself, so our [agent](#agent) runs the code for it.
We call it through an [API](#api).

---

### MBPP

**Mostly Basic Python Problems.** A public dataset of about 1,000 small Python
exercises, published by Google in 2021. It is used to measure how well an AI writes code.

Each task has:

- a short description, for example *"Write a function to find the shared elements from two lists."*
- the function signature to implement, for example `def similar_elements(a, b):`
- about 3 tests written as `assert` lines

In this project, MBPP is the **easy benchmark**, the one used in Sprint 1. The
moulinette gives the agent one task and the agent must return code that passes the tests.
Compare with [SWE-bench](#swe-bench), the hard benchmark.

```text
 task.json ──► agent ──► solution.json ──► moulinette runs the asserts ──► ✅ / ❌
```

---

### Namespace

A dict from names to values. Python looks a name up in this order: **L**ocal
(function) → **E**nclosing functions → **G**lobal (module) → **B**uiltins. `globals()`
and `locals()` return them.

In the sandbox, the LLM's code runs in one dict kept between runs. It holds the code's
variables, `final_answer` and the tools.

**Danger:** a function defined in one of our modules carries that module's globals in
`__globals__`, with `os` and `sys` inside. That's why `__globals__` is refused.

---

### NodeVisitor

`ast.NodeVisitor` walks an [AST](#ast). For each node, it calls the method named
exactly `visit_` + the node's class (`visit_Import`, `visit_Attribute`). If there is
none, it calls `generic_visit`, which visits the children.

Two traps:

- A misnamed method (`visit_ast_import`) is **silently never called**.
- A `visit_X` that doesn't call `self.generic_visit(node)` never looks inside the node.

---

### Package

A folder of Python files that can be imported by name. A folder becomes a package
when it contains an `__init__.py` file.

```text
src/                   ← just a box, not imported
└── agent_smith/       ← the package: import agent_smith
    ├── __init__.py    ← makes the folder a package
    ├── __main__.py    ← runs with: uv run python -m agent_smith
    └── llm/           ← a sub-package: import agent_smith.llm
        ├── __init__.py
        └── client.py  ← a module: from agent_smith.llm.client import LLMClient
```

**Why it matters:**

- **Clean imports:** code is imported by package name, not by file path, so it works
  whatever folder you run it from.
- **`python -m` works:** the moulinette runs `uv run python -m agent_mbpp`. That works
  with a package `agent_mbpp/` that has a `__main__.py`, or with a single module
  `agent_mbpp.py`. The folder structure itself is left to us (subject §VIII).
- **Everything is grouped:** related modules live in one folder, which keeps the
  architecture clear.

---

### Pipe

A one-way channel between two processes: one writes, the other reads. It carries
bytes only, with no message boundaries. A read waits while the pipe is empty, a write
waits while it is full (about 64 KB), and when the writer closes it, the reader gets
[EOF](#eof).

```text
host ──[pipe]──► worker    Init, Exec, ToolResult
host ◄──[pipe]── worker    Ready, Output, ToolCall, FinalAnswer, Done
```

---

### Process / subprocess

A **process** is a running program with its own memory. A **subprocess** is one
started by another process, its parent, with `subprocess.Popen`. Unlike a thread, it
can always be killed, and it can't read its parent's memory.

The sandbox runs the LLM's code in a subprocess, the worker, so an infinite loop can
be killed and the API keys stay in the parent.

---

### Signal

A short message the operating system sends to interrupt a process. Each signal has a
default action (usually: stop). A program can replace it with its own function, a
handler, except for `SIGKILL`.

| Signal | Sent by | In the sandbox |
|---|---|---|
| `SIGINT` | Ctrl+C | the worker ignores it; the host kills the worker and raises `KeyboardInterrupt` |
| `SIGTERM` | "please stop" (the evaluator) | must lead to a clean exit (to do) |
| `SIGKILL` | `kill -9`, `Sandbox.kill()` | stops a runaway worker; can't be caught |

---

### stdin / stdout / stderr

The three standard streams every process starts with:
[file descriptors](#file-descriptor) 0 (input), 1 (normal output) and 2 (errors).

In Python, `sys.stdin`, `sys.stdout` and `sys.stderr` are objects that wrap them.
Replacing the object (`redirect_stdout`) changes what `print` uses, but not fd 1
itself. The worker does both: fds 0 and 1 point to `/dev/null`, and `print` output is
sent to the host as messages.

---

### SWE-bench

*(to be completed)*: the hard benchmark, which fixes real bugs in real GitHub repositories.

---

### Token

A small piece of text, about ¾ of an English word, that an [LLM](#llm) reads and writes.
Providers count usage in tokens, and the subject limits them: MBPP allows at most
6,000 input tokens per task.

---

### YAGNI

*You Aren't Gonna Need It.* Don't build something "in case we need it later": add it
when a real need appears. Example: no `--debug` flag yet, `DEBUG_LEVEL` in `data.py`
is enough for now.
