"""Transkrypcja audio.

Warstwa dostawcow jest tu celowo: do wlasnego uzytku wystarczy darmowy Whisper
liczacy sie lokalnie, ale gdy aplikacja ma obslugiwac wielu uzytkownikow,
podmienia sie dostawce na chmurowy bez ruszania reszty kodu.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class Transcript:
    text: str
    language: str | None = None
    provider: str = "none"

    def is_empty(self) -> bool:
        return not self.text.strip()


class Transcriber(Protocol):
    name: str

    def transcribe(self, audio_path: Path) -> Transcript: ...


class NullTranscriber:
    """Nie robi nic. Uzywany gdy transkrypcja jest wylaczona albo brak ffmpeg."""

    name = "none"

    def transcribe(self, audio_path: Path) -> Transcript:
        return Transcript(text="", provider=self.name)


class LocalWhisperTranscriber:
    """faster-whisper na CPU. Za darmo, bez wysylania audio na zewnatrz."""

    name = "local-whisper"

    def __init__(self, model_size: str = "small") -> None:
        self.model_size = model_size
        self._model = None

    def _load(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:  # pragma: no cover - zalezy od srodowiska
                raise RuntimeError(
                    "Brakuje faster-whisper. Zainstaluj: pip install -e '.[whisper]' "
                    "albo ustaw RECIPES_TRANSCRIBER=none."
                ) from exc
            self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
        return self._model

    def transcribe(self, audio_path: Path) -> Transcript:
        model = self._load()
        segments, info = model.transcribe(str(audio_path), vad_filter=True)
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return Transcript(
            text=text,
            language=getattr(info, "language", None),
            provider=self.name,
        )


def build_transcriber(kind: str, whisper_model: str = "small") -> Transcriber:
    if kind == "local":
        return LocalWhisperTranscriber(whisper_model)
    return NullTranscriber()
