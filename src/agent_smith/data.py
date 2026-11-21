from __future__ import annotations

from enum import Enum


class LLMName(Enum):
    MISTRAL = "MISTRAL"
    GEMINI = "GEMINI"


# API domain of each provider: add one line per new provider
PROVIDERS: dict[str, LLMName] = {
    "api.mistral.ai": LLMName.MISTRAL,
    "generativelanguage.googleapis.com": LLMName.GEMINI,
}

# -----------------------------------
TIMEOUT = 60.0
STOP_SEQUENCES = ["<end_code>", "Observation:"]
