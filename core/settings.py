"""Application settings and environment configuration helpers."""

from __future__ import annotations

from dataclasses import dataclass
import os
from functools import lru_cache


@dataclass
class Settings:
    """Runtime configuration resolved from environment variables."""

    openai_api_key: str = 'blah'
    openai_base_url: str = "http://127.0.0.1:1234/v1"
    openai_model: str = "gpt-4o-mini"
    llm_mode: str = 'http'

    def __post_init__(self) -> None:
        env_api_key = os.getenv("OPENAI_API_KEY")
        env_base_url = os.getenv("OPENAI_API_BASE")
        env_model = os.getenv("OPENAI_MODEL")
        env_mode = os.getenv("LLM_MODE")
        if env_api_key:
            self.openai_api_key = env_api_key
        if env_base_url:
            self.openai_base_url = env_base_url.rstrip("/")
        if env_model:
            self.openai_model = env_model
        if env_mode:
            self.llm_mode = env_mode

    @property
    def resolved_llm_mode(self) -> str:
        """Choose between HTTP or stubbed responses."""

        if self.llm_mode:
            return self.llm_mode
        # Default to stub for safety and testability. Opt-in to HTTP with LLM_MODE=http.
        return "stub"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""

    return Settings()
