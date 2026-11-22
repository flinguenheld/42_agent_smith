from __future__ import annotations

from enum import Enum


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

# -----------------------------------
DEBUG = True

API_TIMEOUT = 60.0
STOP_SEQUENCES = ["<end_code>", "Observation:"]

# MBPP limits (subject VI.1)
MAX_ITERATIONS = 10
