from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_, select

from app.config import get_settings
from app.db import init_db, session_scope
from app.jobs import JobQueue
from app.models import Job, Recipe
from app.pipeline.downloader import parse_shortcode

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

settings = get_settings()
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "web" / "templates"))

queue: JobQueue | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global queue
    init_db()
    queue = JobQueue(settings)
    yield
    queue.shutdown()


app = FastAPI(title="Rolki -> Przepisy", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "web" / "static")), name="static")
# Klatki i miniaturki lezą w katalogu danych, poza pakietem aplikacji.
app.mount("/media", StaticFiles(directory=str(settings.data_dir)), name="media")


def _get_queue() -> JobQueue:
    if queue is None:  # pragma: no cover - tylko przy zlym cyklu zycia
        raise HTTPException(503, "Aplikacja jeszcze wstaje, sprobuj za chwile.")
    return queue


def _recipe_dict(recipe: Recipe) -> dict[str, Any]:
    return {
        "id": recipe.id,
        "shortcode": recipe.shortcode,
        "url": recipe.url,
        "author": recipe.author,
        "title_pl": recipe.title_pl,
        "title_original": recipe.title_original,
        "summary_pl": recipe.summary_pl,
        "source_language": recipe.source_language,
        "servings": recipe.servings,
        "prep_time_min": recipe.prep_time_min,
        "cook_time_min": recipe.cook_time_min,
        "difficulty": recipe.difficulty,
        "ingredients": recipe.ingredients,
        "steps": recipe.steps,
        "equipment_pl": recipe.equipment_pl,
        "tips_pl": recipe.tips_pl,
        "tags_pl": recipe.tags_pl,
        "macros": recipe.macros_dict(),
        "thumbnail_url": f"/media/{recipe.thumbnail_path}" if recipe.thumbnail_path else None,
        "frame_urls": [f"/media/{p}" for p in (recipe.frame_paths or [])],
        "created_at": recipe.created_at.isoformat() if recipe.created_at else None,
    }


# --- Widoki HTML -------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
def index(request: Request, q: str = "") -> HTMLResponse:
    with session_scope() as session:
        query = select(Recipe).order_by(Recipe.created_at.desc())
        if q:
            pattern = f"%{q}%"
            query = query.where(
                or_(
                    Recipe.title_pl.ilike(pattern),
                    Recipe.summary_pl.ilike(pattern),
                    Recipe.author.ilike(pattern),
                )
            )
        recipes = [_recipe_dict(r) for r in session.scalars(query).all()]

    return templates.TemplateResponse(
        request, "index.html", {"recipes": recipes, "q": q}
    )


@app.get("/recipe/{recipe_id}", response_class=HTMLResponse)
def recipe_page(request: Request, recipe_id: int) -> HTMLResponse:
    with session_scope() as session:
        recipe = session.get(Recipe, recipe_id)
        if recipe is None:
            raise HTTPException(404, "Nie ma takiego przepisu.")
        data = _recipe_dict(recipe)
    return templates.TemplateResponse(request, "recipe.html", {"recipe": data})


@app.post("/add")
def add_from_form(url: str = Form(...)) -> RedirectResponse:
    """Wejscie dla formularza - wraca na strone glowna z id zadania w URL-u,
    zeby dzialalo takze bez JavaScriptu."""
    job_id = _get_queue().submit(url.strip())
    return RedirectResponse(f"/?job={job_id}", status_code=303)


# --- API ---------------------------------------------------------------------


@app.post("/api/jobs")
def create_job(payload: dict[str, Any]) -> JSONResponse:
    url = str(payload.get("url", "")).strip()
    if not url:
        raise HTTPException(400, "Podaj pole 'url'.")
    if not parse_shortcode(url):
        raise HTTPException(
            400,
            "To nie wyglada na link do rolki. Oczekiwany format: "
            "https://www.instagram.com/reel/XXXXXXXXX/",
        )
    job_id = _get_queue().submit(url, force=bool(payload.get("force")))
    return JSONResponse({"job_id": job_id, "status": "pending"}, status_code=202)


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    with session_scope() as session:
        job = session.get(Job, job_id)
        if job is None:
            raise HTTPException(404, "Nie ma takiego zadania.")
        return {
            "job_id": job.id,
            "url": job.url,
            "status": job.status.value,
            "message": job.message,
            "recipe_id": job.recipe_id,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        }


@app.get("/api/recipes")
def list_recipes(q: str = "", limit: int = 100) -> dict[str, Any]:
    with session_scope() as session:
        query = select(Recipe).order_by(Recipe.created_at.desc()).limit(min(limit, 500))
        if q:
            pattern = f"%{q}%"
            query = query.where(
                or_(Recipe.title_pl.ilike(pattern), Recipe.summary_pl.ilike(pattern))
            )
        return {"recipes": [_recipe_dict(r) for r in session.scalars(query).all()]}


@app.get("/api/recipes/{recipe_id}")
def get_recipe(recipe_id: int) -> dict[str, Any]:
    with session_scope() as session:
        recipe = session.get(Recipe, recipe_id)
        if recipe is None:
            raise HTTPException(404, "Nie ma takiego przepisu.")
        return _recipe_dict(recipe)


@app.delete("/api/recipes/{recipe_id}")
def delete_recipe(recipe_id: int) -> dict[str, str]:
    with session_scope() as session:
        recipe = session.get(Recipe, recipe_id)
        if recipe is None:
            raise HTTPException(404, "Nie ma takiego przepisu.")
        session.delete(recipe)
    return {"status": "deleted"}
