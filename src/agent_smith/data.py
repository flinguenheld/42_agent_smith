from __future__ import annotations

from enum import Enum, IntEnum


# -------------------------------------------------------------- PROVIDERS ----
class Provider(Enum):
    """LLM API provider; the value is its variable name in .env."""

    COHERE = "COHERE_API_KEY"
    FIREWORKS = "FIREWORKS_API_KEY"
    GEMINI = "GEMINI_API_KEY"
    GROQ = "GROQ_API_KEY"
    MISTRAL = "MISTRAL_API_KEY"
    OPENROUTER = "OPENROUTER_API_KEY"
    PERPLEXITY = "PERPLEXITY_API_KEY"
    TOGETHER = "TOGETHER_API_KEY"


# API domain of each provider: add one line per new provider
PROVIDERS: dict[str, Provider] = {
    "api.cohere.ai": Provider.COHERE,
    "api.fireworks.ai": Provider.FIREWORKS,
    "generativelanguage.googleapis.com": Provider.GEMINI,
    "api.groq.com": Provider.GROQ,
    "api.mistral.ai": Provider.MISTRAL,
    "openrouter.ai": Provider.OPENROUTER,
    "api.perplexity.ai": Provider.PERPLEXITY,
    "api.together.xyz": Provider.TOGETHER,
}


# ------------------------------------------------------------------ DEBUG ----
class DebugLevel(IntEnum):
    """How much debug output to print; each level includes the lower ones."""

    OFF = 0  # nothing
    ON = 1  # each step, final SolutionOutput
    FULL = 2  # + long fields (llm_output, system_prompt)


CODE_THEME = "monokai"  # Pygments style for code in Display.debug


# ------------------------------------------------------------- LLM CLIENT ----
CHAT_PATH = "/chat/completions"  # added to the provider's base URL
API_TIMEOUT = 60.0  # seconds, one HTTP request
API_RETRY_MAX = 3
API_RETRY_DELAY = 1.0  # seconds, multiplied by the retry number
API_RETRY_STATUS = {429, 500, 502, 503, 504}
STOP_SEQUENCES = ["<end_code>", "Observation:"]

# ------------------------------------------------------------------- MBPP ----
BENCHMARK = "mbpp"
MAX_ITERATIONS = 10
MAX_INPUT_TOKENS = 6_000  # cumulative over the whole task
MAX_OUTPUT_TOKENS = 1_500  # cumulative over the whole task
MAX_TOKENS_PER_CALL = 500  # so one reply can't use the whole budget
TIMEOUT_SECONDS = 120.0  # wall-clock, the whole task

# ----------------------------------------------------------------- SANDBOX ---
# Builtins replaced by a stub that raises ForbiddenOperation
BLOCKED_BUILTINS = frozenset(
    {
        "eval",
        "exec",
        "compile",  # run code the policy never checked
        "globals",
        "locals",
        "vars",  # reach namespaces and __builtins__
        "input",
        "breakpoint",
        "help",  # read stdin, start a debugger
        "exit",
        "quit",  # would stop the agent loop (SystemExit)
    }
)
# Builtins removed without a stub: not callable, or dangerous to name
HIDDEN_BUILTINS = frozenset(
    {
        "__loader__",
        "__spec__",  # BuiltinImporter: loads posix, sys...
        "copyright",
        "credits",
        "license",  # interactive-shell helpers
    }
)
# Dunder attributes user code may still use
SAFE_DUNDERS = frozenset({"__init__", "__name__", "__doc__"})
# Not dunders, but they lead to frames, code objects or globals
FORBIDDEN_ATTRS = frozenset(
    {
        "gi_frame",
        "gi_code",
        "gi_yieldfrom",  # generators
        "cr_frame",
        "cr_code",
        "cr_await",
        "cr_origin",  # coroutines
        "ag_frame",
        "ag_code",
        "ag_await",  # async generators
        "f_back",
        "f_builtins",
        "f_code",
        "f_globals",
        "f_locals",  # frames
        "f_trace",
        "tb_frame",
        "tb_next",  # frames, tracebacks
    }
)

DENIED_MODULE_ATTRS: dict[str, frozenset[str]] = {
    "operator": frozenset({"attrgetter", "methodcaller"}),
    "string": frozenset({"Formatter"}),
}

MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_OPEN_FILES = 64

# Audit hook (PEP 578): events refused whatever code asks for them
AUDIT_DENIED_EVENTS = (  # prefixes: "os.exec" covers os.execv, os.execve...
    "os.system",  # processes
    "os.exec",
    "os.posix_spawn",
    "os.spawn",
    "os.fork",
    "os.forkpty",
    "os.kill",
    "os.killpg",
    "subprocess.",
    "pty.",
    "socket.",  # network: urllib, http, ftplib... all go through socket
    "ctypes.",  # native code would bypass the hook
    "sys.settrace",
    "sys.setprofile",
    "sys._current_frames",
    "sys.addaudithook",  # no second hook that could hide events
    "code.__new__",
    "function.__new__",  # hand-made code objects
    "gc.get_",  # gc.get_objects(): every object in the process
)
AUDIT_READ_EVENTS = frozenset({"os.listdir", "os.scandir"})
AUDIT_WRITE_EVENTS = frozenset(
    {
        "os.remove",
        "os.rename",
        "os.mkdir",
        "os.rmdir",
        "os.chmod",
        "os.chown",
        "os.link",
        "os.symlink",
        "os.utime",
        "shutil.rmtree",
    }
)
# Filenames the sandbox gives to the code it compiles: "<sandbox-3> for the
# 3rd run (in tracebacks), "<sandbox-policy>" for the hook's own parse
SANDBOX_FILENAME_PREFIX = "<sandbox-"

# -------------------------------------------------------------- MCP CLIENT ---
# One session: start the server, handshake, one request. Tools are not
# under the sandbox timeout, but a stuck server must not block the agent.
MCP_CALL_TIMEOUT_S = 120.0
# Our MBPP server, at the repo root (the subject wants it there)
MBPP_SERVER_SCRIPT = "mcp_tools_mbpp.py"

# -------------------------------------------------------------- MCP MANUAL ---
# JSON Schema type -> Python type, as the LLM reads it in the manual
JSON_TO_PYTHON = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
    "object": "dict",
    "array": "list",
    "null": "None",
}
