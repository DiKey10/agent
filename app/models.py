from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class JobStatus(str, enum.Enum):
    pending = "pending"
    downloading = "downloading"
    transcribing = "transcribing"
    extracting = "extracting"
    done = "done"
    rejected = "rejected"  # rolka nie byla o gotowaniu
    failed = "failed"


class Job(Base):
    """Jedno zadanie: przerobienie jednego linku na przepis."""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    url: Mapped[str] = mapped_column(Text)
    shortcode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus), default=JobStatus.pending, index=True
    )
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    recipe_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class Recipe(Base):
    __tablename__ = "recipes"
    __table_args__ = (UniqueConstraint("shortcode", name="uq_recipes_shortcode"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # zrodlo
    shortcode: Mapped[str] = mapped_column(String(64), index=True)
    url: Mapped[str] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_s: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # przepis
    title_pl: Mapped[str] = mapped_column(Text)
    title_original: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_pl: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_language: Mapped[str | None] = mapped_column(String(8), nullable=True)

    servings: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prep_time_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cook_time_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(16), nullable=True)

    ingredients: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    equipment_pl: Mapped[list[str]] = mapped_column(JSON, default=list)
    tips_pl: Mapped[list[str]] = mapped_column(JSON, default=list)
    tags_pl: Mapped[list[str]] = mapped_column(JSON, default=list)

    # makro rozbite na kolumny, zeby dalo sie po nim filtrowac i sortowac
    kcal: Mapped[float | None] = mapped_column(Float, nullable=True)
    protein_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fat_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    carbs_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fiber_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    macros_basis: Mapped[str | None] = mapped_column(String(16), nullable=True)
    macros_estimated: Mapped[bool] = mapped_column(Boolean, default=True)

    # media
    thumbnail_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    frame_paths: Mapped[list[str]] = mapped_column(JSON, default=list)

    # material zrodlowy - przydaje sie przy weryfikacji i ponownej ekstrakcji
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    def macros_dict(self) -> dict[str, Any] | None:
        if self.kcal is None and self.protein_g is None:
            return None
        return {
            "kcal": self.kcal,
            "protein_g": self.protein_g,
            "fat_g": self.fat_g,
            "carbs_g": self.carbs_g,
            "fiber_g": self.fiber_g,
            "basis": self.macros_basis,
            "estimated": self.macros_estimated,
        }
