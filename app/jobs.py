"""Kolejka zadan w tle.

Przetworzenie jednej rolki trwa od kilkunastu sekund do kilku minut, wiec nie
moze blokowac requestu HTTP. Uzytkownik dostaje od razu id zadania i odpytuje
o postep, a robota leci w watku obok.

Wykonawca to zwykly ThreadPoolExecutor - caly pipeline jest blokujacy (yt-dlp,
ffmpeg, Whisper, SDK Claude), wiec watki pasuja tu lepiej niz asyncio. Przy
przejsciu na wersje komercyjna to jest miejsce do podmiany na Celery albo RQ.
"""

from __future__ import annotations

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor

from app.config import Settings
from app.db import session_scope
from app.models import Job, JobStatus
from app.pipeline.orchestrator import Pipeline, RecipeRejected

logger = logging.getLogger(__name__)


class JobQueue:
    def __init__(self, settings: Settings, max_workers: int = 2) -> None:
        self.settings = settings
        self.pipeline = Pipeline(settings)
        # Jeden worker na rdzen to za duzo - Whisper i tak zjada CPU, a rownolegle
        # pobieranie z Instagrama szybciej sciaga rate limit niz wyniki.
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="recipe"
        )

    def submit(self, url: str, force: bool = False) -> str:
        job_id = str(uuid.uuid4())
        with session_scope() as session:
            session.add(Job(id=job_id, url=url, status=JobStatus.pending))
        self.executor.submit(self._run, job_id, url, force)
        return job_id

    def _update(
        self,
        job_id: str,
        status: JobStatus,
        message: str | None = None,
        recipe_id: int | None = None,
    ) -> None:
        with session_scope() as session:
            job = session.get(Job, job_id)
            if job is None:
                return
            job.status = status
            if message is not None:
                job.message = message
            if recipe_id is not None:
                job.recipe_id = recipe_id

    def _run(self, job_id: str, url: str, force: bool) -> None:
        def progress(status: str, message: str) -> None:
            self._update(job_id, JobStatus(status), message)

        try:
            with session_scope() as session:
                result = self.pipeline.run(url, session, progress=progress, force=force)
                recipe_id = result.recipe.id
                shortcode = result.recipe.shortcode
                title = result.recipe.title_pl
                cached = result.from_cache

            with session_scope() as session:
                job = session.get(Job, job_id)
                if job:
                    job.shortcode = shortcode
                    job.status = JobStatus.done
                    job.recipe_id = recipe_id
                    job.message = (
                        "Ten przepis byl juz w bazie." if cached else f"Gotowe: {title}"
                    )

        except RecipeRejected as exc:
            self._update(job_id, JobStatus.rejected, exc.reason)
        except Exception as exc:
            logger.exception("Zadanie %s nie powiodlo sie", job_id)
            self._update(job_id, JobStatus.failed, str(exc))

    def shutdown(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=True)
