"""Konsolowy dostep do tego samego pipeline'u, co web.

Przydaje sie do nadrabiania zaleglosci: `rolki add --file linki.txt` przerobi
liste linkow po kolei, bez klikania w przegladarce.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.config import get_settings
from app.db import init_db, session_scope
from app.models import Recipe
from app.pipeline.orchestrator import Pipeline, RecipeRejected


def _process(pipeline: Pipeline, url: str, force: bool) -> bool:
    def progress(_status: str, message: str) -> None:
        print(f"  {message}", flush=True)

    print(f"\n▸ {url}")
    try:
        with session_scope() as session:
            result = pipeline.run(url, session, progress=progress, force=force)
            if result.from_cache:
                print(f"  ✓ Juz w bazie: {result.recipe.title_pl}")
            else:
                print(f"  ✓ {result.recipe.title_pl}  (#{result.recipe.id})")
        return True
    except RecipeRejected as exc:
        print(f"  – Pominieto: {exc.reason}")
        return True  # nie blad - rolka po prostu nie byla o gotowaniu
    except Exception as exc:
        print(f"  ✗ Blad: {exc}", file=sys.stderr)
        return False


def cmd_add(args: argparse.Namespace) -> int:
    urls: list[str] = list(args.urls)
    if args.file:
        content = Path(args.file).read_text(encoding="utf-8")
        urls += [line.strip() for line in content.splitlines() if line.strip()]

    if not urls:
        print("Podaj przynajmniej jeden link albo --file z lista.", file=sys.stderr)
        return 2

    init_db()
    pipeline = Pipeline(get_settings())
    failures = sum(not _process(pipeline, url, args.force) for url in urls)

    print(f"\nPrzetworzono {len(urls) - failures}/{len(urls)} linkow.")
    return 1 if failures else 0


def cmd_list(_args: argparse.Namespace) -> int:
    init_db()
    with session_scope() as session:
        recipes = session.query(Recipe).order_by(Recipe.created_at.desc()).all()
        if not recipes:
            print("Brak przepisow.")
            return 0
        for recipe in recipes:
            kcal = f"{recipe.kcal:.0f} kcal" if recipe.kcal else "—"
            print(f"#{recipe.id:<4} {recipe.title_pl[:56]:<58} {kcal}")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="rolki", description="Zamienia rolki kulinarne na przepisy po polsku."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    add = subparsers.add_parser("add", help="Przerob jedna rolke lub liste rolek")
    add.add_argument("urls", nargs="*", help="Linki do rolek")
    add.add_argument("--file", help="Plik z linkami, po jednym w linii")
    add.add_argument(
        "--force", action="store_true", help="Przetworz od nowa mimo wpisu w bazie"
    )
    add.set_defaults(func=cmd_add)

    listing = subparsers.add_parser("list", help="Pokaz zapisane przepisy")
    listing.set_defaults(func=cmd_list)

    serve = subparsers.add_parser("serve", help="Uruchom aplikacje webowa")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")
    serve.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
