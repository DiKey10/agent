"""Operacje na pliku wideo: wyciagniecie audio i klatek kluczowych.

Wszystko przez ffmpeg. Jesli ffmpeg nie ma w systemie, funkcje zglaszaja
`FFmpegMissing`, a pipeline leci dalej bez transkrypcji i bez klatek -
zamiast wywalac sie w polowie.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


class FFmpegMissing(RuntimeError):
    pass


class MediaError(RuntimeError):
    pass


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    if shutil.which(cmd[0]) is None:
        raise FFmpegMissing(
            f"Nie znaleziono '{cmd[0]}'. Zainstaluj ffmpeg "
            "(macOS: brew install ffmpeg, Ubuntu: apt install ffmpeg)."
        )
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise MediaError(f"{cmd[0]} zwrocil blad: {result.stderr.strip()[:500]}")
    return result


def probe_duration(video_path: Path) -> float:
    result = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(video_path),
        ]
    )
    try:
        return float(json.loads(result.stdout)["format"]["duration"])
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        raise MediaError("Nie udalo sie odczytac dlugosci filmu.") from exc


def extract_audio(video_path: Path, out_path: Path) -> Path:
    """Wyciaga sciezke audio jako 16 kHz mono WAV - format, ktory lubi Whisper."""
    if out_path.exists():
        return out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(out_path),
        ]
    )
    return out_path


def extract_frames(video_path: Path, out_dir: Path, count: int = 6) -> list[Path]:
    """Wycina `count` klatek rozlozonych rowno po calej dlugosci filmu.

    Rowne rozlozenie, a nie wykrywanie zmian sceny, bo w rolkach kulinarnych
    kolejne etapy przygotowania sa rozlozone w czasie mniej wiecej rowno,
    a lista skladnikow czesto pojawia sie na koncu.
    """
    if count <= 0:
        return []

    out_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(out_dir.glob("frame_*.jpg"))
    if len(existing) >= count:
        return existing[:count]

    duration = probe_duration(video_path)
    if duration <= 0:
        raise MediaError("Film ma zerowa dlugosc.")

    frames: list[Path] = []
    for index in range(count):
        # Offset o pol interwalu, zeby nie trafic w czarna pierwsza klatke.
        position = duration * (index + 0.5) / count
        frame_path = out_dir / f"frame_{index:02d}.jpg"
        if not frame_path.exists():
            _run(
                [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    f"{position:.2f}",
                    "-i",
                    str(video_path),
                    "-frames:v",
                    "1",
                    "-vf",
                    "scale=768:-2",
                    "-q:v",
                    "4",
                    str(frame_path),
                ]
            )
        if frame_path.exists():
            frames.append(frame_path)
    return frames
