from __future__ import annotations

import os
from urllib.parse import urlparse

from dotenv import load_dotenv
from termcolor import colored

from agent_smith.data import CHAT_PATH, PROVIDERS, Provider
from agent_smith.display import Display


class ConfigError(Exception):
    pass


class Config:
    """Find the provider from its URL and load its API keys from .env."""

    def __init__(self, url: str, model_name: str) -> None:
        self.url: str = url.rstrip("/")  # base URL, e.g. ".../v1"
        self.chat_url: str = self.url + CHAT_PATH
        self.model_name: str = model_name

        load_dotenv()
        self.name: Provider = self._find_provider()
        self.keys: list[str] = self._load_keys()

        Display.info(f"Provider: {self.name.name} with {len(self.keys)} keys.")

    # ------------------------------------------------------ FIND PROVIDER ----
    def _find_provider(self) -> Provider:
        """Look up the URL's domain in the PROVIDERS table."""

        domain = urlparse(self.url).hostname or ""
        provider = PROVIDERS.get(domain)
        if provider:
            return provider

        raise ConfigError(f"Unknown provider for '{self.url}'")

    # ---------------------------------------------------------- LOAD KEYS ----
    def _load_keys(self) -> list[str]:
        """Read NAME=key1,key2,... from .env and return the list of keys."""

        var_name = self.name.value
        raw = os.getenv(var_name, "")
        keys = [key.strip() for key in raw.split(",") if key.strip()]
        if keys:
            return keys

        raise ConfigError(f"'{var_name}' is missing or empty in .env")

    # ---------------------------------------------------------------- STR ----
    def __str__(self) -> str:
        masked = ",".join(f"***{key[-4:]}" for key in self.keys)
        return f"{self.name.value}={masked}"

    # -------------------------------------------------------------- USAGE ----
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
            for name in Provider
        ]
        domains_title = colored("Accepted provider URLs:", attrs=["bold"])
        domains = ", ".join(colored(domain, "green") for domain in PROVIDERS)
        return f"{title}\n" + "\n".join(lines) + f"\n{domains_title} {domains}"
