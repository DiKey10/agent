"""Testy budowania zapytania do modelu - bez wywolywania API."""

import base64

import pytest

from app.pipeline.extractor import build_content
from app.schemas import ExtractedRecipe, Ingredient, Macros, Step

# Najmniejszy poprawny PNG (1x1 px), zeby nie trzymac binariow w repo.
PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


def _texts(content):
    return "\n".join(block["text"] for block in content if block["type"] == "text")


def test_all_three_sources_reach_the_model(tmp_path):
    frame = tmp_path / "frame_00.jpg"
    frame.write_bytes(PNG_1PX)

    content = build_content(
        caption="Piecz 20 minut w 180C",
        transcript="Dodaj dwie szklanki maki",
        frames=[frame],
        author="kucharz",
        duration_s=45,
    )
    joined = _texts(content)

    assert "Piecz 20 minut w 180C" in joined
    assert "Dodaj dwie szklanki maki" in joined
    assert "kucharz" in joined
    assert sum(1 for block in content if block["type"] == "image") == 1


def test_missing_sources_are_marked_not_dropped():
    """Model musi wiedziec, ze zrodlo jest puste - inaczej zgaduje, ze je pominieto."""
    joined = _texts(build_content(caption="", transcript="", frames=[]))

    assert "(brak opisu)" in joined
    assert "brak - film nie ma mowy" in joined


def test_long_inputs_are_truncated():
    content = build_content(caption="x" * 50_000, transcript="y" * 50_000, frames=[])
    blocks = [block["text"] for block in content if block["type"] == "text"]

    # Pomijamy naglowek bloku - liczy sie tylko wklejona tresc pod nim.
    caption_body = next(b for b in blocks if b.startswith("## Opis posta")).split("\n", 1)[1]
    transcript_body = next(b for b in blocks if b.startswith("## Transkrypcja")).split("\n", 1)[1]

    assert caption_body == "x" * 4000
    assert transcript_body == "y" * 20_000


def test_unreadable_frame_is_skipped(tmp_path):
    good = tmp_path / "ok.jpg"
    good.write_bytes(PNG_1PX)
    weird = tmp_path / "plik.txt"  # nieobslugiwany typ
    weird.write_bytes(b"nie obrazek")

    content = build_content("", "", [good, weird])
    assert sum(1 for block in content if block["type"] == "image") == 1


def test_rejected_recipe_needs_only_the_flag():
    """Gdy rolka nie jest o gotowaniu, model nie musi wypelniac reszty pol."""
    recipe = ExtractedRecipe.model_validate(
        {"is_cooking": False, "reject_reason": "Recenzja restauracji.", "confidence": 0.95}
    )
    assert recipe.is_cooking is False
    assert recipe.ingredients == []
    assert recipe.macros is None


def test_full_recipe_roundtrips_through_the_schema():
    recipe = ExtractedRecipe(
        is_cooking=True,
        confidence=0.9,
        source_language="en",
        title_pl="Naleśniki bananowe",
        ingredients=[Ingredient(name_pl="banan", quantity="2", unit="szt.")],
        steps=[Step(number=1, text_pl="Rozgnieć banany.")],
        macros=Macros(kcal=310.0, protein_g=9.5, basis="per_serving", estimated=True),
    )
    payload = recipe.model_dump(mode="json")

    assert ExtractedRecipe.model_validate(payload) == recipe
    assert payload["macros"]["kcal"] == 310.0


def test_confidence_defaults_to_zero_when_absent():
    assert ExtractedRecipe(is_cooking=True).confidence == 0.0


def test_step_number_must_be_an_integer():
    with pytest.raises(ValueError):
        Step(number="pierwszy", text_pl="Rozgnieć banany.")
