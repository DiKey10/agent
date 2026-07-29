"""Spina caly przebieg: link -> pobranie -> transkrypcja -> Claude -> baza.

Kazdy kosztowny krok jest cache'owany osobno pod shortcode'em rolki. Dzieki temu
gdy ekstrakcja padnie (albo zmienisz prompt), ponowne uruchomienie nie pobiera
wideo od nowa i nie liczy transkrypcji jeszcze raz.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cache import Cache
from app.config import Settings
from app.models import Recipe
from app.pipeline import media
from app.pipeline.downloader import SourceMedia, download
from app.pipeline.extractor import RecipeExtractor
from app.pipeline.transcribe import Transcript, build_transcriber
from app.schemas import ExtractedRecipe

logger = logging.getLogger(__name__)

ProgressFn = Callable[[str, str], None]


class RecipeRejected(RuntimeError):
    """Rolka nie byla o gotowaniu."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass
class PipelineResult:
    recipe: Recipe
    from_cache: bool


class Pipeline:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.cache = Cache(settings.cache_dir)
        self._extractor: RecipeExtractor | None = None
        self._transcriber = None

    # Model i Whisper laduja sie leniwie - bez tego kazdy import aplikacji
    # probowalby czytac klucz API i wciagac model do pamieci.
    @property
    def extractor(self) -> RecipeExtractor:
        if self._extractor is None:
            self._extractor = RecipeExtractor(
                self.settings.anthropic_api_key, self.settings.model
            )
        return self._extractor

    @property
    def transcriber(self):
        if self._transcriber is None:
            self._transcriber = build_transcriber(
                self.settings.transcriber, self.settings.whisper_model
            )
        return self._transcriber

    def _transcribe(self, source: SourceMedia, progress: ProgressFn) -> Transcript:
        if self.settings.transcriber == "none":
            return Transcript(text="", provider="none")

        cached = self.cache.get("transcript", source.shortcode)
        if cached:
            return Transcript(**cached)

        if not media.ffmpeg_available():
            logger.warning("Brak ffmpeg - pomijam transkrypcje dla %s", source.shortcode)
            return Transcript(text="", provider="none")

        progress("transcribing", "Rozpoznaje mowe z filmu...")
        audio_path = source.video_path.parent / "audio.wav"
        try:
            media.extract_audio(source.video_path, audio_path)
            transcript = self.transcriber.transcribe(audio_path)
        except Exception as exc:
            # Brak sciezki audio albo padniety Whisper nie moze zablokowac calosci:
            # z samego opisu i klatek czesto da sie zlozyc przepis.
            logger.warning("Transkrypcja nie powiodla sie (%s): %s", source.shortcode, exc)
            return Transcript(text="", provider="none")

        self.cache.set(
            "transcript",
            source.shortcode,
            {
                "text": transcript.text,
                "language": transcript.language,
                "provider": transcript.provider,
            },
        )
        return transcript

    def _frames(self, source: SourceMedia) -> list[Path]:
        if self.settings.frame_count <= 0 or not media.ffmpeg_available():
            return []
        try:
            return media.extract_frames(
                source.video_path,
                source.video_path.parent / "frames",
                self.settings.frame_count,
            )
        except Exception as exc:
            logger.warning("Nie udalo sie wyciac klatek (%s): %s", source.shortcode, exc)
            return []

    def _extract(
        self,
        source: SourceMedia,
        transcript: Transcript,
        frames: list[Path],
        progress: ProgressFn,
    ) -> ExtractedRecipe:
        cached = self.cache.get("recipe", source.shortcode)
        if cached:
            return ExtractedRecipe.model_validate(cached)

        progress("extracting", "Ukladam przepis po polsku...")
        recipe = self.extractor.extract(
            caption=source.caption,
            transcript=transcript.text,
            frames=frames,
            author=source.author,
            duration_s=source.duration_s,
        )
        self.cache.set("recipe", source.shortcode, recipe.model_dump(mode="json"))
        return recipe

    def run(
        self,
        url: str,
        session: Session,
        progress: ProgressFn | None = None,
        force: bool = False,
    ) -> PipelineResult:
        emit: ProgressFn = progress or (lambda status, message: None)

        emit("downloading", "Pobieram rolke...")
        source = download(url, self.settings.media_dir, self.settings.max_duration_s)

        if not force:
            existing = session.scalar(
                select(Recipe).where(Recipe.shortcode == source.shortcode)
            )
            if existing:
                return PipelineResult(recipe=existing, from_cache=True)

        transcript = self._transcribe(source, emit)
        frames = self._frames(source)
        extracted = self._extract(source, transcript, frames, emit)

        if not extracted.is_cooking:
            raise RecipeRejected(
                extracted.reject_reason or "To nie jest rolka o gotowaniu."
            )

        recipe = _persist(session, source, extracted, transcript, frames)
        return PipelineResult(recipe=recipe, from_cache=False)


def _relative(path: Path | None, root: Path) -> str | None:
    """Sciezki trzymamy wzglednie do katalogu danych, zeby baza przetrwala
    przeniesienie projektu w inne miejsce."""
    if path is None:
        return None
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _persist(
    session: Session,
    source: SourceMedia,
    extracted: ExtractedRecipe,
    transcript: Transcript,
    frames: list[Path],
) -> Recipe:
    from app.config import get_settings

    data_dir = get_settings().data_dir
    macros = extracted.macros

    recipe = session.scalar(select(Recipe).where(Recipe.shortcode == source.shortcode))
    if recipe is None:
        recipe = Recipe(shortcode=source.shortcode)
        session.add(recipe)

    recipe.url = source.url
    recipe.author = source.author
    recipe.posted_at = source.posted_at
    recipe.duration_s = source.duration_s

    recipe.title_pl = extracted.title_pl or "Przepis bez tytulu"
    recipe.title_original = extracted.title_original
    recipe.summary_pl = extracted.summary_pl
    recipe.source_language = extracted.source_language or transcript.language

    recipe.servings = extracted.servings
    recipe.prep_time_min = extracted.prep_time_min
    recipe.cook_time_min = extracted.cook_time_min
    recipe.difficulty = extracted.difficulty

    recipe.ingredients = [i.model_dump(mode="json") for i in extracted.ingredients]
    recipe.steps = [s.model_dump(mode="json") for s in extracted.steps]
    recipe.equipment_pl = extracted.equipment_pl
    recipe.tips_pl = extracted.tips_pl
    recipe.tags_pl = extracted.tags_pl

    recipe.kcal = macros.kcal if macros else None
    recipe.protein_g = macros.protein_g if macros else None
    recipe.fat_g = macros.fat_g if macros else None
    recipe.carbs_g = macros.carbs_g if macros else None
    recipe.fiber_g = macros.fiber_g if macros else None
    recipe.macros_basis = macros.basis if macros else None
    recipe.macros_estimated = macros.estimated if macros else True

    recipe.thumbnail_path = _relative(source.thumbnail_path, data_dir)
    recipe.frame_paths = [p for f in frames if (p := _relative(f, data_dir))]

    recipe.transcript = transcript.text or None
    recipe.caption = source.caption or None

    session.flush()
    return recipe
