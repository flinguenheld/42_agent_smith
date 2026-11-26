"""MBPP tool: does a candidate solution pass its tests?"""

from __future__ import annotations

import json

from agent_smith.sandbox import SandboxConfig, execute


def run_tests(code: str, test_list: list[str]) -> str:
    """Run `code`, then each assert of `test_list`, in a fresh sandbox.

    Returns only a JSON string: {"success": bool, "output": str}. success
    is true only if every assert passed; output says what went wrong.
    """
    program = "\n".join([code, *test_list])
    result = execute(program, SandboxConfig())
    return json.dumps({
        "success": result.ok,
        "output": result.to_observation(),
    })
