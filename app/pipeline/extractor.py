"""Zamiana surowego materialu z rolki na uporzadkowany przepis po polsku.

Do Claude leci wszystko naraz - transkrypcja audio, opis posta i klatki wideo -
bo w rolkach kulinarnych informacje sa rozrzucone miedzy te trzy zrodla:
ilosci czesto sa tylko na ekranie, kroki tylko w narracji, a czas pieczenia
tylko w opisie. Model dostaje komplet i sam sklada z tego calosc.

Odpowiedz jest wymuszona schematem (structured outputs), wiec nie parsujemy
tekstu recznie i nie ma ryzyka, ze model odda cos innego niz przepis.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any

from app.schemas import ExtractedRecipe

logger = logging.getLogger(__name__)

MAX_CAPTION_CHARS = 4000
MAX_TRANSCRIPT_CHARS = 20000

SYSTEM_PROMPT = """\
Jestes asystentem, ktory zamienia rolki kulinarne z Instagrama w uporzadkowane \
przepisy po polsku.

Dostajesz trzy zrodla opisujace ten sam film: transkrypcje sciezki audio, opis \
posta i klatki z wideo. Traktuj je jako uzupelniajace sie. W rolkach kulinarnych \
ilosci skladnikow sa zwykle wypisane na ekranie (klatki), kolejnosc czynnosci \
pada w narracji (transkrypcja), a czasy i temperatury bywaja tylko w opisie. \
Skladaj przepis ze wszystkich trzech.

Zasady:

1. Klasyfikacja. Ustaw is_cooking=true tylko wtedy, gdy film faktycznie pokazuje \
przygotowanie jedzenia lub napoju i da sie z niego odtworzyc przepis. Recenzja \
restauracji, film o zakupach spozywczych, samo jedzenie posilku albo prezentacja \
sprzetu bez gotowania to nie jest przepis - wtedy is_cooking=false, wypelnij \
reject_reason i zostaw reszte pol pusta.

2. Jezyk. Cala tresc wyjsciowa pisz po polsku, niezaleznie od jezyka oryginalu. \
Tlumacz nazwy skladnikow na polskie odpowiedniki uzywane w kuchni (heavy cream -> \
smietana kremowka 30%, all-purpose flour -> maka pszenna). W title_original zostaw \
tytul w oryginale, a w source_language kod jezyka zrodla.

3. Jednostki. Przeliczaj na metryczne: cup, oz, lb, F na g, ml i stopnie Celsjusza. \
Zaokraglaj do sensownych wartosci kuchennych - 1 cup maki to 120 g, nie 118.29 g.

4. Wierność. Zapisuj to, co faktycznie jest w materiale. Nie dodawaj skladnikow \
ani krokow, ktorych nie ma. Gdy ilosc nie padla, zostaw quantity jako null - to \
uczciwsze niz zgadywanie.

5. Makro. Oszacuj wartosci odzywcze na porcje na podstawie skladnikow i ustaw \
estimated=true. Jesli w rolce padly konkretne liczby, uzyj ich i ustaw \
estimated=false. Gdy nie da sie sensownie oszacowac, zostaw macros jako null.
"""


def _read_image_block(path: Path) -> dict[str, Any] | None:
    suffix = path.suffix.lower()
    media_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(suffix)
    if media_type is None:
        return None
    try:
        data = base64.standard_b64encode(path.read_bytes()).decode("ascii")
    except OSError:
        logger.warning("Nie udalo sie odczytac klatki %s", path)
        return None
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": data},
    }


def build_content(
    caption: str,
    transcript: str,
    frames: list[Path],
    author: str | None = None,
    duration_s: int | None = None,
) -> list[dict[str, Any]]:
    """Sklada bloki tresci dla jednego zapytania do modelu."""
    content: list[dict[str, Any]] = []

    header = ["# Rolka z Instagrama"]
    if author:
        header.append(f"Autor: {author}")
    if duration_s:
        header.append(f"Dlugosc: {duration_s} s")
    content.append({"type": "text", "text": "\n".join(header)})

    caption = (caption or "").strip()
    content.append(
        {
            "type": "text",
            "text": "## Opis posta\n"
            + (caption[:MAX_CAPTION_CHARS] if caption else "(brak opisu)"),
        }
    )

    transcript = (transcript or "").strip()
    content.append(
        {
            "type": "text",
            "text": "## Transkrypcja audio\n"
            + (
                transcript[:MAX_TRANSCRIPT_CHARS]
                if transcript
                else "(brak - film nie ma mowy albo transkrypcja jest wylaczona)"
            ),
        }
    )

    if frames:
        content.append(
            {
                "type": "text",
                "text": (
                    f"## Klatki z wideo ({len(frames)}, w kolejnosci chronologicznej)\n"
                    "Odczytaj z nich napisy, listy skladnikow i etapy przygotowania."
                ),
            }
        )
        for frame in frames:
            if block := _read_image_block(frame):
                content.append(block)

    content.append(
        {
            "type": "text",
            "text": "Wyodrebnij przepis zgodnie z zasadami z system promptu.",
        }
    )
    return content


class RecipeExtractor:
    def __init__(self, api_key: str, model: str = "claude-opus-5") -> None:
        if not api_key:
            raise ValueError(
                "Brak klucza ANTHROPIC_API_KEY. Ustaw go w pliku .env."
            )
        import anthropic

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def extract(
        self,
        caption: str,
        transcript: str,
        frames: list[Path],
        author: str | None = None,
        duration_s: int | None = None,
    ) -> ExtractedRecipe:
        content = build_content(caption, transcript, frames, author, duration_s)

        response = self.client.messages.parse(
            model=self.model,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": content}],
            output_format=ExtractedRecipe,
        )

        if response.stop_reason == "refusal":
            raise RuntimeError(
                "Model odmowil przetworzenia tego materialu ze wzgledow bezpieczenstwa."
            )

        recipe = response.parsed_output
        if recipe is None:
            raise RuntimeError(
                "Model nie zwrocil poprawnego przepisu "
                f"(stop_reason={response.stop_reason})."
            )
        return recipe
