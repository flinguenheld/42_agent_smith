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

### EAFP / LBYL

- **EAFP**, *Easier to Ask Forgiveness than Permission*: try the action, catch the error
  (`try`/`except`). The usual Python style.
- **LBYL**, *Look Before You Leap*: check every condition with `if` first.

Keep the `try` block small, so it doesn't hide unrelated bugs.

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

### Package

A folder of Python files that can be imported by name. A folder becomes a package
when it contains an `__init__.py` file.

```text
src/                   ← just a box, not imported
└── agent_smith/       ← the package: import agent_smith
    ├── __init__.py    ← makes the folder a package
    ├── __main__.py    ← runs with: uv run python -m agent_smith
    └── llm_client.py  ← a module: from agent_smith.llm_client import LlmClient
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

### SWE-bench

*(to be completed)*: the hard benchmark, which fixes real bugs in real GitHub repositories.

---

### Token

A small piece of text, about ¾ of an English word, that an [LLM](#llm) reads and writes.
Providers count usage in tokens, and the subject limits them: MBPP allows at most
6,000 input tokens per task.
