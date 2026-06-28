from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any, Awaitable, Callable, Protocol, TypeVar
from uuid import UUID

from services.ai import OpenAIESGClient
from services.analysis.gap_detector import GapDetector
from services.analysis.scoring import ScoringEngine
from services.parsing import ParsingEngine, ParsingError
from services.schemas import (
    AnalysisResult,
    AnalysisStep,
    EntrepriseContext,
    ESRSRequirement,
    ExtractedESRSData,
)

logger = logging.getLogger(__name__)
T = TypeVar("T")


class AnalysisError(Exception):
    """Raised when the CSRD analysis pipeline cannot recover."""


class RapportForAnalysis(Protocol):
    id: UUID
    file_path: Path
    filename: str
    entreprise: EntrepriseContext


class ESRSRepository(Protocol):
    async def get_rapport_for_analysis(self, rapport_id: UUID) -> RapportForAnalysis:
        raise NotImplementedError

    async def list_requirements_for_company(self, entreprise: EntrepriseContext) -> list[ESRSRequirement]:
        raise NotImplementedError

    async def persist_analysis_result(self, result: AnalysisResult) -> None:
        raise NotImplementedError

    async def enqueue_pdf_generation(self, rapport_id: UUID) -> None:
        raise NotImplementedError


class AnalysisEngine:
    """
    Main CSRD analysis orchestrator.

    The pipeline is intentionally explicit: every step is timed and recorded so
    a client-facing score remains explainable and debuggable.
    """

    def __init__(
        self,
        parsing_engine: ParsingEngine,
        ai_client: OpenAIESGClient,
        esrs_repository: ESRSRepository,
        gap_detector: GapDetector,
        scoring_engine: ScoringEngine,
    ):
        self.parsing = parsing_engine
        self.ai = ai_client
        self.esrs = esrs_repository
        self.gaps = gap_detector
        self.scoring = scoring_engine

    async def analyze_rapport(self, rapport_id: UUID) -> AnalysisResult:
        result = AnalysisResult(rapport_id=rapport_id, status="failed")
        steps: list[AnalysisStep] = []
        errors: list[str] = []

        try:
            rapport = await self._record_step(
                "load_rapport",
                steps,
                lambda: self.esrs.get_rapport_for_analysis(rapport_id),
            )

            parsed_document = await self._record_step(
                "parse_document",
                steps,
                lambda: self.parsing.parse(rapport.file_path, rapport.filename),
            )
            result.parsed_document = parsed_document

            requirements = await self._record_step(
                "load_esrs_requirements",
                steps,
                lambda: self.esrs.list_requirements_for_company(rapport.entreprise),
            )

            classification = await self._record_step(
                "classify_document",
                steps,
                lambda: self._retry_with_backoff(
                    lambda: self.ai.classify_document(parsed_document.chunks),
                    max_retries=2,
                ),
            )
            result.classification = classification

            extractions = await self._record_step(
                "extract_esrs_data",
                steps,
                lambda: self._retry_with_backoff(
                    lambda: self.ai.extract_esrs_data(parsed_document.chunks, requirements),
                    max_retries=3,
                ),
            )
            result.extractions = extractions

            gaps = await self._record_step(
                "detect_gaps",
                steps,
                lambda: async_value(self.gaps.detect_gaps(extractions, rapport.entreprise)),
            )
            result.gaps = gaps

            scores = [
                self.scoring.calculate_esrs_score(
                    requirement,
                    find_extraction(requirement, extractions),
                    rapport.entreprise.secteur_naf,
                )
                for requirement in requirements
            ]
            global_score = await self._record_step(
                "calculate_score",
                steps,
                lambda: async_value(self.scoring.calculate_global_score(scores)),
            )
            result.score = global_score

            await self._record_step(
                "persist_results",
                steps,
                lambda: self.esrs.persist_analysis_result(result),
            )

            await self._record_step(
                "enqueue_pdf_generation",
                steps,
                lambda: self.esrs.enqueue_pdf_generation(rapport_id),
                optional=True,
            )

            result.status = "success" if not errors else "partial"
        except (ParsingError, AnalysisError) as exc:
            logger.exception("Analysis failed for rapport %s", rapport_id)
            errors.append(str(exc))
            result.status = "failed"
        except Exception as exc:
            logger.exception("Unexpected analysis failure for rapport %s", rapport_id)
            errors.append(f"Unexpected analysis failure: {exc}")
            result.status = "failed"

        result.steps = steps
        result.errors = errors
        return result

    async def _retry_with_backoff(
        self,
        factory: Callable[[], Awaitable[T]],
        max_retries: int = 3,
    ) -> T:
        delay = 0.5
        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                return await factory()
            except Exception as exc:
                last_error = exc
                if attempt == max_retries - 1:
                    break
                logger.warning("Retryable analysis call failed on attempt %s: %s", attempt + 1, exc)
                await asyncio.sleep(delay)
                delay *= 2
        raise AnalysisError(f"Retry exhausted: {last_error}")

    async def _record_step(
        self,
        name: str,
        steps: list[AnalysisStep],
        factory: Any,
        *,
        optional: bool = False,
    ) -> Any:
        started_at = time.perf_counter()
        try:
            value = await factory()
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            steps.append(
                AnalysisStep(
                    name=name,
                    status="skipped" if optional else "failed",
                    duration_ms=duration_ms,
                    error=str(exc),
                )
            )
            if optional:
                logger.warning("Optional analysis step %s failed: %s", name, exc)
                return None
            raise

        steps.append(
            AnalysisStep(
                name=name,
                status="success",
                duration_ms=int((time.perf_counter() - started_at) * 1000),
            )
        )
        return value


async def async_value(value: T) -> T:
    return value


def find_extraction(
    requirement: ESRSRequirement,
    extractions: list[ExtractedESRSData],
) -> ExtractedESRSData | None:
    aliases = {requirement.full_code, requirement.code_esrs, requirement.identifiant}
    return next((extraction for extraction in extractions if extraction.esrs_code in aliases), None)
