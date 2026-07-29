"""Schematy przepisu.

`ExtractedRecipe` jest jednoczesnie schematem JSON, ktory dostaje Claude
(structured outputs), i modelem walidujacym odpowiedz. Jeden zrodlowy opis
ksztaltu danych zamiast dwoch, ktore moglyby sie rozjechac.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Ingredient(BaseModel):
    name_pl: str = Field(description="Nazwa skladnika po polsku, np. 'maka pszenna'")
    quantity: str | None = Field(
        default=None,
        description="Ilosc jako tekst, np. '250' albo '1/2'. null jesli nie podano.",
    )
    unit: str | None = Field(
        default=None,
        description="Jednostka po polsku: g, ml, lyzka, szklanka, szt. null jesli nie podano.",
    )
    note: str | None = Field(
        default=None, description="Dopisek, np. 'w temperaturze pokojowej'"
    )


class Step(BaseModel):
    number: int = Field(description="Numer kroku, liczony od 1")
    text_pl: str = Field(description="Tresc kroku po polsku, tryb rozkazujacy")


class Macros(BaseModel):
    kcal: float | None = None
    protein_g: float | None = None
    fat_g: float | None = None
    carbs_g: float | None = None
    fiber_g: float | None = None
    basis: Literal["per_serving", "per_100g", "total"] = Field(
        default="per_serving",
        description="Do czego odnosza sie wartosci",
    )
    estimated: bool = Field(
        default=True,
        description="true jesli makro zostalo oszacowane, false jesli podane wprost w rolce",
    )


class ExtractedRecipe(BaseModel):
    """To, co Claude zwraca dla pojedynczej rolki."""

    is_cooking: bool = Field(
        description=(
            "true tylko jesli rolka faktycznie pokazuje przygotowanie jedzenia lub "
            "napoju i da sie z niej odtworzyc przepis"
        )
    )
    reject_reason: str | None = Field(
        default=None,
        description="Gdy is_cooking=false: jedno zdanie po polsku, dlaczego to nie jest przepis",
    )
    confidence: float = Field(
        default=0.0, description="Pewnosc klasyfikacji w zakresie 0.0-1.0"
    )

    source_language: str | None = Field(
        default=None, description="Kod jezyka oryginalu, np. 'en', 'pl', 'it'"
    )
    title_pl: str | None = Field(default=None, description="Tytul przepisu po polsku")
    title_original: str | None = Field(
        default=None, description="Tytul w jezyku oryginalu, jesli inny niz polski"
    )
    summary_pl: str | None = Field(
        default=None, description="Dwa zdania o tym, co to za danie"
    )

    servings: int | None = Field(default=None, description="Liczba porcji")
    prep_time_min: int | None = Field(default=None, description="Czas przygotowania w minutach")
    cook_time_min: int | None = Field(default=None, description="Czas obrobki cieplnej w minutach")
    difficulty: Literal["latwe", "srednie", "trudne"] | None = None

    ingredients: list[Ingredient] = Field(default_factory=list)
    steps: list[Step] = Field(default_factory=list)
    equipment_pl: list[str] = Field(
        default_factory=list, description="Potrzebny sprzet, np. 'blender', 'piekarnik'"
    )
    tips_pl: list[str] = Field(
        default_factory=list, description="Wskazowki i triki wspomniane w rolce"
    )
    tags_pl: list[str] = Field(
        default_factory=list,
        description="Tagi po polsku, np. 'wegetarianskie', 'obiad', 'szybkie'",
    )

    macros: Macros | None = Field(
        default=None, description="Wartosci odzywcze. null jesli nie da sie oszacowac."
    )
