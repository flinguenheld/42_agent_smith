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
    SUMMARY = 1  # config, final SolutionOutput
    STEPS = 2  # + one short line per step
    FULL = 3  # + every field of each model, as JSON


DEBUG_LEVEL = DebugLevel.STEPS

# ------------------------------------------------------------- LLM CLIENT ----
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
