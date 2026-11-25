"""Messages exchanged between the host (parent and the worker (child).

Framing: JSON Lines, one JSON object per line, UTF-8, over binary pipes.
Never pickle: the parent must not execute anything the child sends.
"""

from typing import (
    IO,
    Annotated,
    Any,
    Literal,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
)

MAX_LINE_BYTES = 4 * 1024 * 1024


class ProtocolError(Exception):
    """Malformed, oversized or unknown message."""


class _Msg(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# parent -> child


class Init(_Msg):
    type: Literal["init"] = "init"
    config: dict[str, Any]  # SandboxConfig.model_dump()
    tool_names: list[str] = []


class Exec(_Msg):
    type: Literal["exec"] = "exec"
    code: str


class ToolResult(_Msg):
    type: Literal["tool_result"] = "tool_result"
    call_id: int
    ok: bool
    value: str  # result or error text


# child -> parent


class Ready(_Msg):
    type: Literal["ready"] = "ready"


class Output(_Msg):
    type: Literal["output"] = "output"
    stream: Literal["stdout", "stderr"]
    data: str


class ToolCall(_Msg):
    type: Literal["tool_call"] = "tool_call"
    call_id: int
    name: str
    kwargs: dict[str, Any] = {}


class FinalAnswer(_Msg):
    type: Literal["final_answer"] = "final_answer"
    value: str


class Done(_Msg):
    type: Literal["done"] = "done"
    status: str
    error: str | None = None
    control: Literal["system_exit", "keyboard_interrupt"] | None = None
    exit_code: int | None = None


ToParent = Annotated[
    Ready | Output | ToolCall | FinalAnswer | Done, Field(discriminator="type")
]
ToChild = Annotated[Init | Exec | ToolResult, Field(discriminator="type")]
_to_parent: TypeAdapter = TypeAdapter(ToParent)
_to_child: TypeAdapter = TypeAdapter(ToChild)


def encode(msg: _Msg) -> bytes:
    """One message -> one JSON line (bytes, newline included)."""
    return msg.model_dump_json().encode("utf-8") + b"\n"


def _decode(line: bytes, adapter: TypeAdapter) -> Any:
    if len(line) > MAX_LINE_BYTES or not line.endswith(b"\n"):
        raise ProtocolError("message too long or not newline-terminated")
    try:
        return adapter.validate_json(line)
    except ValidationError as exc:
        raise ProtocolError(f"invalid message: {exc}") from exc


def decode_from_child(line: bytes) -> Any:
    """Parent side: bytes of one line -> a ToParent message."""
    return _decode(line, _to_parent)


def send(stream: IO[bytes], msg: _Msg) -> None:
    stream.write(encode(msg))
    stream.flush()


def receive_from_parent(stream: IO[bytes]) -> Any | None:
    """Child side (blocking). A ToChild message, or None on EOF."""
    line = stream.readline(MAX_LINE_BYTES + 1)
    if not line:
        return None  # EOF: the parent is gone
    return _decode(line, _to_child)
