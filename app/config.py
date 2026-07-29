from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Konfiguracja czytana z .env i zmiennych srodowiskowych."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="RECIPES_",
        extra="ignore",
    )

    # Klucz Claude API czytamy pod jego wlasna nazwa, bez prefiksu RECIPES_.
    anthropic_api_key: str = ""

    model: str = "claude-opus-5"
    transcriber: Literal["local", "none"] = "local"
    whisper_model: str = "small"
    frame_count: int = 6

    data_dir: Path = Path("./data")

    # Maksymalna dlugosc rolki - dluzsze filmy odrzucamy zanim pobierzemy audio.
    max_duration_s: int = 900

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"

    @property
    def media_dir(self) -> Path:
        return self.data_dir / "media"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "recipes.db"

    def ensure_dirs(self) -> None:
        for path in (self.data_dir, self.cache_dir, self.media_dir):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    import os

    settings = Settings()
    # ANTHROPIC_API_KEY nie ma prefiksu RECIPES_, wiec bierzemy je recznie.
    if not settings.anthropic_api_key:
        settings.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    settings.ensure_dirs()
    return settings
