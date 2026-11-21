"""Tests for extract_code(): pull the Python code out of an LLM reply.

The stop sequences already removed "<end_code>", so replies end with ```.
"""

from agent_smith.extract import extract_code

FENCE = "```"


# ------------------------------------------------- Rule 2: both fences ----
def test_python_fence() -> None:
    reply = f"Thought: easy.\n{FENCE}python\nprint(2 ** 10)\n{FENCE}"
    assert extract_code(reply) == "print(2 ** 10)"


def test_bare_fence() -> None:
    reply = f"Thought: easy.\n{FENCE}\nprint(2 ** 10)\n{FENCE}"
    assert extract_code(reply) == "print(2 ** 10)"


# --------------------------------------------- Rule 1: first block only ----
def test_first_block_only() -> None:
    reply = (
        f"{FENCE}python\nprint('first')\n{FENCE}\n"
        "Observation: all tests passed!\n"
        f"{FENCE}python\nprint('second')\n{FENCE}"
    )
    assert extract_code(reply) == "print('first')"


def test_text_after_block_is_ignored() -> None:
    reply = f"{FENCE}python\nx = 1\n{FENCE}\nNow I wait for the result."
    assert extract_code(reply) == "x = 1"


# ------------------------------------------- Rule 3: no block -> None ----
def test_no_code_block() -> None:
    assert extract_code("Thought: I think the answer is 42.") is None


def test_empty_reply() -> None:
    assert extract_code("") is None


def test_unclosed_block() -> None:
    reply = f"Thought: ...\n{FENCE}python\nprint('cut by max_tokens"
    assert extract_code(reply) is None


# ------------------------------------------------------- Rule 4: strip ----
def test_strip_blank_lines_around_code() -> None:
    reply = f"{FENCE}python\n\n\nprint(1)\n\n\n{FENCE}"
    assert extract_code(reply) == "print(1)"


# --------------------------------------------- The code is kept intact ----
def test_multiline_code_keeps_indentation() -> None:
    code = "def add(a, b):\n    return a + b\n\nprint(add(1, 2))"
    reply = f"Thought: ...\n{FENCE}python\n{code}\n{FENCE}"
    assert extract_code(reply) == code


def test_code_with_triple_quoted_string() -> None:
    code = 'code = """\ndef f(x):\n    return x\n"""\nprint(code)'
    reply = f"{FENCE}python\n{code}\n{FENCE}"
    assert extract_code(reply) == code
