from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from services.schemas import (
    DocumentChunk,
    DocumentClassification,
    ESRSRequirement,
    ExtractedESRSData,
    GapDescription,
    Severity,
)

try:  # optional at import time for tests and local development
    from openai import AsyncOpenAI
except Exception:  # pragma: no cover - exercised only when dependency is absent
    AsyncOpenAI = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class AIClientError(Exception):
    """Raised when LLM extraction cannot be completed safely."""


class OpenAIESGClient:
    """
    OpenAI client specialized for ESG tasks.

    If the SDK or API key is unavailable, methods fall back to deterministic
    heuristics where possible. This keeps the MVP testable without real API calls.
    """

    def __init__(self, api_key: str | None, model: str = "gpt-4o"):
        self.model = model
        self.prompts_dir = Path(__file__).parent / "prompts"
        self.client = AsyncOpenAI(api_key=api_key) if api_key and AsyncOpenAI else None

    async def classify_document(self, chunks: list[DocumentChunk]) -> DocumentClassification:
        sample = "\n".join(chunk.content for chunk in chunks[:8])
        framework_scores = {
            "CSRD": score_keywords(sample, ["csrd", "esrs", "double materialite"]),
            "GRI": score_keywords(sample, ["gri", "global reporting initiative"]),
            "SASB": score_keywords(sample, ["sasb"]),
            "TCFD": score_keywords(sample, ["tcfd", "climate-related financial"]),
        }
        framework, score = max(framework_scores.items(), key=lambda item: item[1])
        if score <= 0:
            framework = "unknown"

        return DocumentClassification(
            framework=framework,  # type: ignore[arg-type]
            confidence=min(1.0, score / 3),
            language="fr" if score_keywords(sample, ["rapport", "emissions", "salaries"]) else "en",
            notes="Heuristic classification; LLM not required for MVP routing.",
        )

    async def extract_esrs_data(
        self,
        chunks: list[DocumentChunk],
        esrs_requirements: list[ESRSRequirement],
    ) -> list[ExtractedESRSData]:
        relevant_chunks = prefilter_chunks(chunks, esrs_requirements, limit=14)
        if not self.client:
            return fallback_extract_esrs_data(relevant_chunks, esrs_requirements)

        prompt = self._load_prompt("extract_esrs_data.txt")
        content = render_prompt(
            prompt,
            {
                "sector": "unknown",
                "workforce": "unknown",
                "obligation_date": "unknown",
                "esrs_list": json.dumps(
                    [requirement.model_dump(mode="json") for requirement in esrs_requirements],
                    ensure_ascii=False,
                ),
                "document_chunks": json.dumps(
                    [
                        {
                            "id": str(chunk.id),
                            "page": chunk.page_number,
                            "section": chunk.section_title,
                            "content": chunk.content[:2200],
                        }
                        for chunk in relevant_chunks
                    ],
                    ensure_ascii=False,
                ),
            },
        )

        started_at = time.perf_counter()
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": "Tu es un analyste CSRD senior. Reponds uniquement en JSON valide.",
                    },
                    {"role": "user", "content": content},
                ],
            )
        except Exception as exc:
            logger.exception("OpenAI ESRS extraction failed; using deterministic fallback")
            return fallback_extract_esrs_data(relevant_chunks, esrs_requirements, error=str(exc))

        raw = response.choices[0].message.content or "{}"
        parsed = self._parse_json_safely(raw)
        parsed.setdefault("meta", {})
        parsed["meta"]["processing_time_ms"] = int((time.perf_counter() - started_at) * 1000)

        try:
            return [
                ExtractedESRSData.model_validate(item)
                for item in parsed.get("extractions", [])
            ]
        except ValidationError as exc:
            logger.warning("Invalid OpenAI extraction schema; falling back: %s", exc)
            return fallback_extract_esrs_data(relevant_chunks, esrs_requirements, error=str(exc))

    async def generate_gap_description(
        self,
        requirement: ESRSRequirement,
        extracted: ExtractedESRSData | None,
        company_sector: str,
    ) -> GapDescription:
        if extracted is None or not extracted.present:
            return GapDescription(
                title=f"Donnee manquante pour {requirement.full_code}",
                description=(
                    f"L'exigence {requirement.full_code} n'a pas ete retrouvee dans le rapport. "
                    f"Pour le secteur {company_sector}, cette absence peut bloquer la revue CSRD."
                ),
                action="Collecter la donnee source, documenter la methode et ajouter la preuve au rapport.",
                severity=Severity.CRITIQUE if requirement.obligatoire else Severity.MINEUR,
            )

        if extracted.confidence < 0.7:
            return GapDescription(
                title=f"Donnee partielle pour {requirement.full_code}",
                description=(
                    f"La donnee existe mais la confiance d'extraction est de {extracted.confidence:.0%}."
                ),
                action="Completer la source documentaire et citer la page ou la methode de calcul.",
                severity=Severity.MAJEUR,
            )

        return GapDescription(
            title=f"Point de controle {requirement.full_code}",
            description="La donnee est presente mais doit rester verifiable dans l'audit trail.",
            action="Conserver la source, la page et la methode dans le dossier de preuve.",
            severity=Severity.INFO,
        )

    def _load_prompt(self, name: str) -> str:
        path = self.prompts_dir / name
        if not path.exists():
            raise AIClientError(f"Prompt not found: {path}")
        return path.read_text(encoding="utf-8")

    def _parse_json_safely(self, content: str) -> dict[str, Any]:
        cleaned = content.strip()
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
            if not match:
                logger.warning("No JSON object found in LLM response")
                return {"extractions": [], "meta": {"parse_error": "no_json_object"}}
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError as exc:
                logger.warning("JSON parsing failed after cleanup: %s", exc)
                return {"extractions": [], "meta": {"parse_error": str(exc)}}

        if not isinstance(parsed, dict):
            return {"extractions": [], "meta": {"parse_error": "root_not_object"}}
        return parsed


def render_prompt(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{{ " + key + " }}", value)
        rendered = rendered.replace("{{" + key + "}}", value)
    return rendered


def score_keywords(text: str, keywords: list[str]) -> int:
    lowered = text.lower()
    return sum(1 for keyword in keywords if keyword.lower() in lowered)


def prefilter_chunks(
    chunks: list[DocumentChunk],
    requirements: list[ESRSRequirement],
    *,
    limit: int,
) -> list[DocumentChunk]:
    if not chunks:
        return []

    keywords = set()
    for requirement in requirements:
        keywords.update(tokenize_requirement(requirement.code_esrs))
        keywords.update(tokenize_requirement(requirement.identifiant))
        keywords.update(tokenize_requirement(requirement.intitule))

    scored: list[tuple[int, DocumentChunk]] = []
    for chunk in chunks:
        lowered = chunk.content.lower()
        score = sum(1 for keyword in keywords if keyword and keyword in lowered)
        scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    selected = [chunk for score, chunk in scored[:limit] if score > 0]
    return selected or chunks[:limit]


def tokenize_requirement(value: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z0-9-]{2,}", value)}


def fallback_extract_esrs_data(
    chunks: list[DocumentChunk],
    requirements: list[ESRSRequirement],
    *,
    error: str | None = None,
) -> list[ExtractedESRSData]:
    combined = "\n".join(chunk.content for chunk in chunks)
    lowered = combined.lower()
    results: list[ExtractedESRSData] = []

    for requirement in requirements:
        tokens = tokenize_requirement(requirement.code_esrs) | tokenize_requirement(requirement.identifiant)
        title_tokens = tokenize_requirement(requirement.intitule)
        title_hits = sum(1 for token in title_tokens if token in lowered)
        code_hit = any(token in lowered for token in tokens)
        present = code_hit or title_hits >= 2
        source_chunk = next(
            (
                chunk
                for chunk in chunks
                if any(token in chunk.content.lower() for token in tokens | title_tokens)
            ),
            None,
        )
        flags = ["fallback_heuristique"]
        if error:
            flags.append("llm_indisponible")
        if not present and requirement.obligatoire:
            flags.append("manquant_critique")

        results.append(
            ExtractedESRSData(
                esrs_code=requirement.full_code,
                present=present,
                value=source_chunk.content[:500] if present and source_chunk else None,
                page_source=source_chunk.page_number if source_chunk else None,
                confidence=0.62 if present else 0.35,
                notes="Extraction heuristique MVP sans appel API reel.",
                flags=flags,
            )
        )

    return results

