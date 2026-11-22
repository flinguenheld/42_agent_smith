"""The texts we send to the LLM: system prompt and fixed messages.

This module only holds wording. The loop in agent.py decides when each
text is sent and builds the messages list.
"""

from agent_smith.models import MBPPTaskInput

SYSTEM_PROMPT = '''\
You are an expert Python programmer. You solve one coding task by
writing code that is executed for you.

At each step, answer in this exact format:
Thought: <short reasoning>
```python
<code>
```<end_code>

Rules:
- Write exactly one ```python block per answer.
- Use print() to see values. The output is sent back to you as
  "Observation:". Never write an Observation yourself.
- Test your solution before you submit it.

Functions you can call in your code:
- run_tests(code: str, test_list: list[str]) -> str
  Runs the tests against your code and returns the results.
- final_answer(code: str)
  Submits your final function code and ends the task.

Example:
Thought: I'll write the function, then test it.
```python
code = """
def add(a, b):
    return a + b
"""
print(run_tests(code, ["assert add(1, 2) == 3"]))
```<end_code>'''

NO_CODE_MESSAGE = (
    "No valid code block found. Answer with one ```python block, "
    "then <end_code>."
)


def build_task_message(task: MBPPTaskInput) -> str:
    """Turn an MBPP task into the first user message."""

    tests = "\n".join(task.test_list)
    return (
        f"Task: {task.task_definition}\n"
        f"Signature: {task.function_definition}\n"
        f"Tests:\n{tests}"
    )
