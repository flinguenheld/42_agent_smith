"""Turn nested data (e.g. model_dump()) into readable text.

Unlike JSON, multi-line strings (code, prompts, LLM replies) keep their
real line breaks instead of showing "\\n".
"""


def pretty_format(value: object) -> str:
    """Return value as indented, human-readable text."""

    return "\n".join(_to_lines(value, ""))


def _to_lines(value: object, pad: str) -> list[str]:
    """Return value as lines; nested items are indented under pad."""

    lines: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if _is_block(item):
                lines.append(f"{pad}{key}:")
                lines += _to_lines(item, pad + "  ")
            else:
                lines.append(f"{pad}{key}: {item!r}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            if _is_block(item):
                lines.append(f"{pad}[{index}]")
                lines += _to_lines(item, pad + "  ")
            else:
                lines.append(f"{pad}[{index}] {item!r}")
    elif isinstance(value, str):
        lines = [pad + line for line in value.splitlines()]
    else:
        lines = [pad + repr(value)]
    return lines


def _is_block(item: object) -> bool:
    """Return True if item needs its own indented lines."""

    if isinstance(item, (dict, list)):
        return len(item) > 0
    return isinstance(item, str) and "\n" in item
