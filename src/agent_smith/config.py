from __future__ import annotations

import os
from enum import Enum
from urllib.parse import urlparse

from dotenv import load_dotenv
from termcolor import colored

from agent_smith.display import print_info


class ConfigError(Exception):
    pass


class LLMName(Enum):
    MISTRAL = "MISTRAL"


# API domain of each provider: add one line per new provider
PROVIDERS: dict[str, LLMName] = {
    "api.mistral.ai": LLMName.MISTRAL,
}


class Config:
    """Find the provider from its URL and load its API keys from .env."""

    def __init__(self, url: str) -> None:
        self.url: str = url

        load_dotenv()
        self.name: LLMName = self._find_provider()
        self.keys: list[str] = self._load_keys()

        print_info(f"Provider: {self.name.value} with {len(self.keys)} keys.")

    def _find_provider(self) -> LLMName:
        """Look up the URL's domain in the PROVIDERS table."""

        domain = urlparse(self.url).hostname or ""
        llm_name = PROVIDERS.get(domain)
        if llm_name:
            return llm_name

        raise ConfigError(f"Unknown provider for '{self.url}'")

    def _load_keys(self) -> list[str]:
        """Read NAME=key1,key2,... from .env and return the list of keys."""

        var_name = self.name.value
        raw = os.getenv(var_name, "")
        keys = [key.strip() for key in raw.split(",") if key.strip()]
        if keys:
            return keys

        raise ConfigError(f"'{var_name}' is missing or empty in .env")

    # -------------------------------------------------------------
    # -------------------------------------------------------------------------
    def __str__(self) -> str:
        masked = ",".join(f"***{key[-4:]}" for key in self.keys)
        return f"{self.name.value}={masked}"

    @staticmethod
    def usage() -> str:
        title = colored(
            "--\n"
            "Config usage:\n"
            "Fill in .env with the API keys of your provider:",
            attrs=["bold"],
        )
        placeholder = colored("key1,key2,...", "yellow")
        lines = [
            f"  {colored(name.value, 'cyan')}={placeholder}"
            for name in LLMName
        ]
        domains_title = colored("Accepted provider URLs:", attrs=["bold"])
        domains = ", ".join(colored(domain, "green") for domain in PROVIDERS)
        return f"{title}\n" + "\n".join(lines) + f"\n{domains_title} {domains}"
