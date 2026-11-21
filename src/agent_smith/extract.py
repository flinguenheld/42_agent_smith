"""Pull the Python code out of a raw LLM reply."""

import re

# ```python (or a bare ```) + newline, then the code, then the closing ```
# - (?:python)?  the language tag is optional
# - (.*?)        lazy: stops at the FIRST closing ```, so only block 1 is kept
# - re.DOTALL    lets "." match newlines, the code spans several lines
CODE_BLOCK = re.compile(r"```(?:python)?[ \t]*\n(.*?)```", re.DOTALL)


def extract_code(llm_output: str) -> str | None:
    """Return the code of the first complete code block, or None.

    None means "no usable code": no block, an unclosed block (reply cut
    by max_tokens) or an empty block. The caller tells the LLM to retry.
    """

    match = CODE_BLOCK.search(llm_output)
    if match is None:
        return None

    code = match.group(1).strip()
    return code or None
