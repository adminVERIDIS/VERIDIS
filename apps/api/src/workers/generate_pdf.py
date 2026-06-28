from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from models import RapportCSRD
from services.pdf_generator import PDFDocument, PDFRenderer
from services.schemas import AnalysisResult

try:
    from celery import Celery
except ImportError:  # pragma: no cover - import fallback for local unit tests.
    Celery = None


class PDFJobRepository(Protocol):
    async def get_report_with_company(self, rapport_id: UUID) -> RapportCSRD:
        """Return the report with its company relationship loaded."""

    async def get_analysis_result(self, rapport_id: UUID) -> AnalysisResult:
        """Return the latest persisted analysis result for the report."""

    async def mark_pdf_ready(self, rapport_id: UUID, document: PDFDocument) -> None:
        """Persist generated PDF metadata and storage URL."""

    async def mark_pdf_failed(self, rapport_id: UUID, error: str) -> None:
        """Persist a failed PDF generation state."""


@dataclass(frozen=True)
class PDFWorkerDependencies:
    repository: PDFJobRepository
    renderer: PDFRenderer


_dependencies: PDFWorkerDependencies | None = None


def configure_pdf_worker(dependencies: PDFWorkerDependencies) -> None:
    global _dependencies
    _dependencies = dependencies


def _create_celery_app() -> Celery | None:
    if Celery is None:
        return None

    broker_url = os.getenv("VERIDIS_CELERY_BROKER_URL", "redis://localhost:6379/0")
    result_backend = os.getenv("VERIDIS_CELERY_RESULT_BACKEND", broker_url)
    app = Celery("veridis_pdf", broker=broker_url, backend=result_backend)
    app.conf.update(
        task_default_queue="pdf-generation",
        task_time_limit=30,
        task_soft_time_limit=20,
        worker_prefetch_multiplier=1,
    )
    return app


celery_app = _create_celery_app()


async def generate_pdf_job(rapport_id: UUID) -> PDFDocument:
    if _dependencies is None:
        raise RuntimeError("PDF worker dependencies are not configured.")

    repository = _dependencies.repository
    renderer = _dependencies.renderer

    try:
        rapport = await repository.get_report_with_company(rapport_id)
        analyse = await repository.get_analysis_result(rapport_id)
        document = await renderer.generate(rapport, analyse)
        await repository.mark_pdf_ready(rapport_id, document)
        return document
    except Exception as exc:
        await repository.mark_pdf_failed(rapport_id, str(exc))
        raise


def _run_job(rapport_id: str) -> dict[str, str | int | None]:
    document = asyncio.run(generate_pdf_job(UUID(rapport_id)))
    return {
        "filename": document.filename,
        "file_size": document.file_size,
        "page_count": document.page_count,
        "checksum_sha256": document.checksum_sha256,
        "url": document.url,
    }


if celery_app is not None:

    @celery_app.task(name="veridis.generate_pdf", bind=True)
    def generate_pdf_task(self, rapport_id: str) -> dict[str, str | int | None]:
        return _run_job(rapport_id)

else:

    def generate_pdf_task(rapport_id: str) -> dict[str, str | int | None]:
        return _run_job(rapport_id)
