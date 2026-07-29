"""Pobieranie rolki przez yt-dlp.

Bierzemy tylko linki, ktore uzytkownik sam wkleil. Nie logujemy sie na konto
Instagrama i nie przegladamy niczego automatycznie - to swiadoma decyzja:
zwykle pobranie publicznego posta jest stabilne, a scrapowanie na zalogowanym
koncie lamie regulamin serwisu i konczy sie blokada.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SHORTCODE_RE = re.compile(
    r"instagram\.com/(?:reels?|p|tv)/(?P<code>[A-Za-z0-9_-]+)", re.IGNORECASE
)


class DownloadError(RuntimeError):
    pass


@dataclass
class SourceMedia:
    shortcode: str
    url: str
    video_path: Path
    thumbnail_path: Path | None = None
    caption: str = ""
    author: str | None = None
    duration_s: int | None = None
    posted_at: datetime | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def parse_shortcode(url: str) -> str | None:
    """Wyciaga identyfikator posta z linku. None gdy to nie jest link do rolki."""
    match = _SHORTCODE_RE.search(url)
    return match.group("code") if match else None


def _pick_thumbnail(directory: Path, stem: str) -> Path | None:
    for suffix in (".jpg", ".jpeg", ".png", ".webp"):
        candidate = directory / f"{stem}{suffix}"
        if candidate.exists():
            return candidate
    return None


def download(url: str, media_dir: Path, max_duration_s: int = 900) -> SourceMedia:
    """Pobiera wideo i metadane. Ponowne wywolanie dla tego samego linku
    korzysta z pliku juz lezacego na dysku."""
    try:
        import yt_dlp
    except ImportError as exc:  # pragma: no cover - zalezy od srodowiska
        raise DownloadError(
            "Brakuje yt-dlp. Zainstaluj zaleznosci: pip install -e ."
        ) from exc

    shortcode = parse_shortcode(url)
    if not shortcode:
        raise DownloadError(
            "To nie wyglada na link do rolki na Instagramie. "
            "Oczekiwany format: https://www.instagram.com/reel/XXXXXXXXX/"
        )

    target_dir = media_dir / shortcode
    target_dir.mkdir(parents=True, exist_ok=True)

    options = {
        "outtmpl": str(target_dir / "video.%(ext)s"),
        "format": "mp4/bestvideo+bestaudio/best",
        "writeinfojson": False,
        "writethumbnail": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "retries": 3,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        try:
            info = ydl.extract_info(url, download=True)
        except Exception as exc:
            raise DownloadError(f"Nie udalo sie pobrac rolki: {exc}") from exc

    duration = info.get("duration")
    if duration and duration > max_duration_s:
        raise DownloadError(
            f"Film trwa {int(duration)}s, limit to {max_duration_s}s. "
            "To raczej nie jest rolka."
        )

    video_path = next(
        (p for p in sorted(target_dir.glob("video.*")) if p.suffix != ".json"), None
    )
    if video_path is None or not video_path.exists():
        raise DownloadError("yt-dlp nie zapisal pliku wideo.")

    posted_at = None
    if timestamp := info.get("timestamp"):
        posted_at = datetime.fromtimestamp(timestamp, tz=timezone.utc)

    return SourceMedia(
        shortcode=shortcode,
        url=url,
        video_path=video_path,
        thumbnail_path=_pick_thumbnail(target_dir, "video"),
        caption=(info.get("description") or "").strip(),
        author=info.get("uploader") or info.get("channel"),
        duration_s=int(duration) if duration else None,
        posted_at=posted_at,
        extra={"title": info.get("title"), "like_count": info.get("like_count")},
    )
