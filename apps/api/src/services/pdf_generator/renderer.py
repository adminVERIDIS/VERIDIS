from __future__ import annotations

import hashlib
import math
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID

from jinja2 import Environment, FileSystemLoader, Template, select_autoescape

from models import RapportCSRD
from services.schemas import AnalysisResult, ESRSScore, ExtractedESRSData, Gap, Severity

try:
    from playwright.async_api import async_playwright
except ImportError:  # pragma: no cover - exercised only when dependency is missing.
    async_playwright = None


ESRS_PAGE_ORDER = [
    "ESRS 1",
    "ESRS 2",
    "E1",
    "E2",
    "E3",
    "E4",
    "E5",
    "S1",
    "S2",
    "S3",
    "S4",
    "G1",
]

SEVERITY_WEIGHT = {
    Severity.CRITIQUE: 4,
    Severity.MAJEUR: 3,
    Severity.MINEUR: 2,
    Severity.INFO: 1,
}

STATUS_LABELS = {
    "complete": "Conforme",
    "partial": "Partiel",
    "missing": "Non conforme",
    "na": "Non applicable",
}


@dataclass(frozen=True)
class PDFOptions:
    format: str = "A4"
    margin: dict[str, str] = field(
        default_factory=lambda: {
            "top": "20mm",
            "right": "20mm",
            "bottom": "20mm",
            "left": "20mm",
        }
    )
    print_background: bool = True
    prefer_css_page_size: bool = True
    timeout_ms: int = 10_000


@dataclass(frozen=True)
class PDFDocument:
    content: bytes
    filename: str
    file_size: int
    checksum_sha256: str
    page_count: int
    generated_at: datetime
    render_time_ms: int
    content_type: str = "application/pdf"
    storage_key: str | None = None
    url: str | None = None


class S3Client(Protocol):
    async def upload_pdf(self, key: str, body: bytes, content_type: str) -> str:
        """Upload PDF bytes and return a signed or public download URL."""


class PDFRenderer:
    """Render offline CSRD conformity reports as professional A4 PDFs."""

    def __init__(
        self,
        *,
        template_dir: str | Path | None = None,
        s3_client: S3Client | None = None,
        playwright: Any | None = None,
        options: PDFOptions | None = None,
    ) -> None:
        base_dir = Path(__file__).resolve().parent
        self.template_dir = Path(template_dir) if template_dir else base_dir / "templates"
        self.style_path = base_dir / "styles" / "print.css"
        self.s3_client = s3_client
        self.playwright = playwright
        self.options = options or PDFOptions()
        self.environment = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(enabled_extensions=("html", "xml")),
            trim_blocks=True,
            lstrip_blocks=True,
            cache_size=96,
        )
        self.environment.filters.update(
            {
                "date_fr": self._format_date,
                "pct": self._format_percent,
                "score": self._format_score,
                "severity_label": self._severity_label,
                "status_label": self._status_label,
            }
        )

    async def generate(
        self,
        rapport: RapportCSRD,
        analyse: AnalysisResult,
        template_name: str = "rapport_conformite.html",
    ) -> PDFDocument:
        started_at = time.perf_counter()
        html = self._render_html(rapport, analyse, template_name)
        html = self._inline_assets(html)
        pdf_bytes = await self._html_to_pdf(html)
        checksum = hashlib.sha256(pdf_bytes).hexdigest()
        storage_key = self._storage_key(rapport, analyse)
        download_url = None

        if self.s3_client is not None:
            download_url = await self.s3_client.upload_pdf(
                storage_key,
                pdf_bytes,
                "application/pdf",
            )

        generated_at = datetime.now(UTC)
        return PDFDocument(
            content=pdf_bytes,
            filename=storage_key.rsplit("/", 1)[-1],
            file_size=len(pdf_bytes),
            checksum_sha256=checksum,
            page_count=self._count_report_pages(html),
            generated_at=generated_at,
            render_time_ms=round((time.perf_counter() - started_at) * 1000),
            storage_key=storage_key if self.s3_client is not None else None,
            url=download_url,
        )

    def _render_html(
        self,
        rapport: RapportCSRD,
        analyse: AnalysisResult,
        template_name: str,
    ) -> str:
        template: Template = self.environment.get_template(template_name)
        context = self._build_context(rapport, analyse)
        return template.render(context)

    async def _html_to_pdf(self, html: str) -> bytes:
        self._assert_offline_html(html)

        if self.playwright is not None:
            return await self._render_with_playwright(self.playwright, html)

        if async_playwright is None:
            raise RuntimeError(
                "Playwright is required to render PDF reports. Install the "
                "'playwright' package and browser binaries."
            )

        async with async_playwright() as playwright_context:
            return await self._render_with_playwright(playwright_context, html)

    def _inline_assets(self, html: str) -> str:
        css = self.style_path.read_text(encoding="utf-8")
        inlined = html.replace("{{ INLINE_PRINT_CSS }}", css)
        self._assert_offline_html(inlined)
        return inlined

    async def _render_with_playwright(self, playwright_context: Any, html: str) -> bytes:
        browser = await playwright_context.chromium.launch(args=["--disable-dev-shm-usage"])
        try:
            page = await browser.new_page(
                viewport={"width": 1240, "height": 1754},
                device_scale_factor=1,
            )
            await page.set_content(
                html,
                wait_until="networkidle",
                timeout=self.options.timeout_ms,
            )
            return await page.pdf(
                format=self.options.format,
                print_background=self.options.print_background,
                prefer_css_page_size=self.options.prefer_css_page_size,
                margin=self.options.margin,
                timeout=self.options.timeout_ms,
            )
        finally:
            await browser.close()

    def _build_context(self, rapport: RapportCSRD, analyse: AnalysisResult) -> dict[str, Any]:
        entreprise = self._safe_get(rapport, "entreprise")
        company_name = self._safe_get(entreprise, "raison_sociale", "Entreprise non renseignee")
        siren = self._safe_get(entreprise, "siren", "Non renseigne")
        sector = self._safe_get(entreprise, "secteur_naf", "Non renseigne")
        workforce = self._safe_get(entreprise, "effectif", "Non renseigne")
        exercise = self._safe_get(rapport, "exercice", datetime.now(UTC).year)
        score_value = self._global_score(rapport, analyse)
        score_status = self._score_status(score_value)
        esrs_pages = self._build_esrs_pages(analyse)
        actions = self._build_actions(analyse.gaps)
        severity_counts = self._severity_counts(analyse.gaps)
        extraction_count = len(analyse.extractions)
        present_count = sum(1 for extraction in analyse.extractions if extraction.present)
        coverage_ratio = analyse.score.coverage_ratio if analyse.score else 0.0

        return {
            "generated_at": datetime.now(UTC),
            "total_pages": 21,
            "brand": {
                "name": "VERIDIS",
                "product": "CSRD Validator",
            },
            "company": {
                "name": company_name,
                "siren": siren,
                "sector": sector,
                "workforce": workforce,
            },
            "report": {
                "id": str(self._safe_get(rapport, "id", analyse.rapport_id)),
                "exercise": exercise,
                "deadline": self._safe_get(rapport, "date_echeance"),
                "source": self._source_label(self._safe_get(rapport, "fichier_source")),
                "status": self._safe_get(rapport, "statut", analyse.status),
            },
            "score": {
                "value": score_value,
                "raw_value": analyse.score.raw_score if analyse.score else score_value,
                "status": score_status,
                "label": self._score_label(score_status),
                "coverage": coverage_ratio,
                "sector_percentile": analyse.score.percentile_sectoriel if analyse.score else None,
                "trend": analyse.score.tendance if analyse.score else "inconnue",
            },
            "dashboard": {
                "esrs_completed": sum(1 for item in esrs_pages if item["status"] == "complete"),
                "esrs_partial": sum(1 for item in esrs_pages if item["status"] == "partial"),
                "esrs_missing": sum(1 for item in esrs_pages if item["status"] == "missing"),
                "extraction_count": extraction_count,
                "present_count": present_count,
                "coverage_ratio": coverage_ratio,
                "severity_counts": severity_counts,
                "score_bars": self._score_bars(esrs_pages),
                "gap_heatmap": self._gap_heatmap(esrs_pages),
            },
            "esrs_pages": esrs_pages,
            "gaps": sorted(
                (self._gap_view(gap) for gap in analyse.gaps),
                key=lambda item: (-item["severity_weight"], -item["impact_score"]),
            ),
            "action_pages": self._action_pages(actions),
            "timeline": self._timeline(actions),
            "methodology": {
                "steps": [step.model_dump() for step in analyse.steps],
                "errors": analyse.errors,
                "limits": [
                    "Le score mesure la couverture documentaire, la qualite des preuves et les "
                    "ecarts detectes sur les exigences ESRS analysees.",
                    "Le rapport ne constitue pas une assurance externe ni une opinion d'audit.",
                    "Les informations estimees doivent etre validees par les responsables metier "
                    "avant depot reglementaire.",
                ],
            },
        }

    def _build_esrs_pages(self, analyse: AnalysisResult) -> list[dict[str, Any]]:
        score_by_code = {
            self._normalise_code(score.esrs_code): score for score in (analyse.score.details if analyse.score else [])
        }
        extractions_by_code = self._group_extractions(analyse.extractions)
        gaps_by_code = self._group_gaps(analyse.gaps)
        pages: list[dict[str, Any]] = []

        for code in ESRS_PAGE_ORDER:
            normalised = self._normalise_code(code)
            score = score_by_code.get(normalised)
            score_value = self._esrs_score_value(score)
            status = score.status if score is not None else "missing"
            pages.append(
                {
                    "code": code,
                    "title": self._esrs_title(code),
                    "score": score_value,
                    "status": status,
                    "status_label": self._status_label(status),
                    "confidence": score.confidence if score is not None else 0.0,
                    "weight": score.weight if score is not None else 0.0,
                    "explanation": score.explanation if score is not None else "Aucune analyse detaillee disponible.",
                    "penalties": score.penalties if score is not None else [],
                    "bonuses": score.bonuses if score is not None else [],
                    "extractions": extractions_by_code.get(normalised, []),
                    "gaps": gaps_by_code.get(normalised, []),
                    "gap_count": len(gaps_by_code.get(normalised, [])),
                    "requirement_count": len(extractions_by_code.get(normalised, [])),
                }
            )

        return pages

    def _build_actions(self, gaps: list[Gap]) -> list[dict[str, Any]]:
        sorted_gaps = sorted(
            gaps,
            key=lambda gap: (
                -SEVERITY_WEIGHT.get(gap.severity, 0),
                -gap.impact_score,
                gap.deadline_days,
            ),
        )
        actions = []
        for index, gap in enumerate(sorted_gaps, start=1):
            deadline_days = max(gap.deadline_days, 1)
            actions.append(
                {
                    "rank": index,
                    "title": gap.description,
                    "action": gap.action_required,
                    "deadline": f"J+{deadline_days}",
                    "deadline_days": deadline_days,
                    "owner": self._owner_for_gap(gap),
                    "severity": gap.severity.value,
                    "severity_label": self._severity_label(gap.severity),
                    "severity_weight": SEVERITY_WEIGHT.get(gap.severity, 0),
                    "category": gap.category.value,
                    "impact_score": round(gap.impact_score, 1),
                    "resources": gap.resources,
                    "effort": self._effort_label(gap),
                }
            )

        return actions

    def _action_pages(self, actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        page_specs = [
            ("Priorites critiques", "Corriger les ecarts qui bloquent la conformite et la revue."),
            ("Qualite des donnees", "Completer les preuves et fiabiliser les sources."),
            ("Gouvernance", "Clarifier les controles, proprietaires et validations."),
            ("Feuille de route", "Sequencer les actions restantes avant echeance."),
        ]
        chunks = self._chunk(actions, 5)
        pages = []
        for index, (title, description) in enumerate(page_specs):
            pages.append(
                {
                    "page_number": 17 + index,
                    "title": title,
                    "description": description,
                    "items": chunks[index] if index < len(chunks) else [],
                }
            )
        return pages

    def _timeline(self, actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        phases = [
            ("0-30 jours", 30),
            ("31-60 jours", 60),
            ("61-90 jours", 90),
            ("90+ jours", math.inf),
        ]
        previous_limit = 0
        timeline = []
        for label, limit in phases:
            items = [
                action
                for action in actions
                if previous_limit < action["deadline_days"] <= limit
            ]
            timeline.append(
                {
                    "label": label,
                    "count": len(items),
                    "items": items[:4],
                }
            )
            previous_limit = int(limit) if math.isfinite(limit) else previous_limit
        return timeline

    def _score_bars(self, esrs_pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "code": item["code"],
                "score": item["score"],
                "width": max(0, min(100, item["score"])),
                "status": item["status"],
            }
            for item in esrs_pages
        ]

    def _gap_heatmap(self, esrs_pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        max_gap_count = max((item["gap_count"] for item in esrs_pages), default=1) or 1
        return [
            {
                "code": item["code"],
                "gap_count": item["gap_count"],
                "intensity": round(item["gap_count"] / max_gap_count, 2),
            }
            for item in esrs_pages
        ]

    def _group_extractions(
        self,
        extractions: list[ExtractedESRSData],
    ) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for extraction in extractions:
            key = self._normalise_code(extraction.esrs_code)
            grouped.setdefault(key, []).append(
                {
                    "code": extraction.esrs_code,
                    "present": extraction.present,
                    "value": extraction.value,
                    "value_estimated": extraction.value_estimated,
                    "value_unit": extraction.value_unit,
                    "page_source": extraction.page_source,
                    "confidence": extraction.confidence,
                    "notes": extraction.notes,
                    "flags": extraction.flags,
                }
            )
        return grouped

    def _group_gaps(self, gaps: list[Gap]) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        known_keys = {self._normalise_code(code) for code in ESRS_PAGE_ORDER}
        for gap in gaps:
            key = self._normalise_code(gap.requirement_code or "")
            if key not in known_keys:
                key = self._infer_gap_code(gap)
            grouped.setdefault(key, []).append(self._gap_view(gap))
        return grouped

    def _gap_view(self, gap: Gap) -> dict[str, Any]:
        return {
            "id": gap.id,
            "requirement_code": gap.requirement_code or "Non rattache",
            "severity": gap.severity.value,
            "severity_label": self._severity_label(gap.severity),
            "severity_weight": SEVERITY_WEIGHT.get(gap.severity, 0),
            "category": gap.category.value,
            "description": gap.description,
            "impact_score": round(gap.impact_score, 1),
            "action_required": gap.action_required,
            "deadline_days": gap.deadline_days,
            "resources": gap.resources,
            "confidence": gap.confidence,
        }

    def _infer_gap_code(self, gap: Gap) -> str:
        candidate = (gap.requirement_code or gap.id or "").upper()
        for code in ESRS_PAGE_ORDER:
            normalised = self._normalise_code(code)
            if normalised in candidate.replace(" ", ""):
                return normalised
        return "ESRS1"

    def _global_score(self, rapport: RapportCSRD, analyse: AnalysisResult) -> float:
        if analyse.score is not None:
            return round(float(analyse.score.adjusted_score), 1)
        persisted_score = self._safe_get(rapport, "score_global")
        return round(float(persisted_score), 1) if persisted_score is not None else 0.0

    def _esrs_score_value(self, score: ESRSScore | None) -> float:
        if score is None or score.score is None:
            return 0.0
        if score.max_score <= 0:
            return 0.0
        return round(max(0.0, min(100.0, (score.score / score.max_score) * 100)), 1)

    def _score_status(self, score: float) -> str:
        if score >= 80:
            return "conforme"
        if score >= 50:
            return "partiel"
        return "non_conforme"

    def _score_label(self, status: str) -> str:
        return {
            "conforme": "Conforme",
            "partiel": "Partiel",
            "non_conforme": "Non conforme",
        }[status]

    def _status_label(self, status: str) -> str:
        return STATUS_LABELS.get(status, status.replace("_", " ").title())

    def _severity_label(self, severity: Severity | str) -> str:
        value = severity.value if isinstance(severity, Severity) else severity
        return {
            "critique": "Critique",
            "majeur": "Majeur",
            "mineur": "Mineur",
            "info": "Information",
        }.get(value, value.title())

    def _severity_counts(self, gaps: list[Gap]) -> dict[str, int]:
        counts = {"critique": 0, "majeur": 0, "mineur": 0, "info": 0}
        for gap in gaps:
            counts[gap.severity.value] = counts.get(gap.severity.value, 0) + 1
        return counts

    def _normalise_code(self, value: str) -> str:
        text = value.upper().strip()
        text = re.sub(r"[^A-Z0-9]+", "", text)
        if text.startswith("ESRS") and len(text) > 4:
            suffix = text[4:]
            if re.match(r"^[ESG][0-9]$", suffix):
                return suffix
            return f"ESRS{suffix}"
        match = re.match(r"^([ESG][0-9])", text)
        return match.group(1) if match else text or "ESRS1"

    def _esrs_title(self, code: str) -> str:
        return {
            "ESRS 1": "Exigences generales",
            "ESRS 2": "Informations generales",
            "E1": "Changement climatique",
            "E2": "Pollution",
            "E3": "Eau et ressources marines",
            "E4": "Biodiversite et ecosystemes",
            "E5": "Utilisation des ressources",
            "S1": "Effectifs de l'entreprise",
            "S2": "Travailleurs de la chaine de valeur",
            "S3": "Communautes affectees",
            "S4": "Consommateurs et utilisateurs finaux",
            "G1": "Conduite des affaires",
        }.get(code, code)

    def _owner_for_gap(self, gap: Gap) -> str:
        category = gap.category.value
        if "methodologie" in category or "tracabilite" in category:
            return "Direction finance / ESG"
        if "incoherence" in category:
            return "Controle interne"
        return "Responsable donnees metier"

    def _effort_label(self, gap: Gap) -> str:
        if gap.deadline_days <= 30 or gap.impact_score >= 80:
            return "Eleve"
        if gap.deadline_days <= 60 or gap.impact_score >= 50:
            return "Moyen"
        return "Faible"

    def _chunk(self, values: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
        return [values[index : index + size] for index in range(0, len(values), size)]

    def _storage_key(self, rapport: RapportCSRD, analyse: AnalysisResult) -> str:
        report_id = self._safe_get(rapport, "id", analyse.rapport_id)
        exercise = self._safe_get(rapport, "exercice", "unknown")
        return f"reports/{report_id}/rapport-csrd-{exercise}.pdf"

    def _source_label(self, source: Any) -> str:
        if isinstance(source, dict):
            for key in ("filename", "name", "path"):
                value = source.get(key)
                if value:
                    return str(value)
        if source:
            return str(source)
        return "Document source non renseigne"

    def _format_date(self, value: datetime | date | None) -> str:
        if value is None:
            return "Non renseigne"
        return value.strftime("%d/%m/%Y")

    def _format_percent(self, value: float | int | None) -> str:
        if value is None:
            return "0 %"
        numeric = float(value)
        if numeric <= 1:
            numeric *= 100
        return f"{numeric:.0f} %"

    def _format_score(self, value: float | int | None) -> str:
        if value is None:
            return "0"
        numeric = float(value)
        return str(int(numeric)) if numeric.is_integer() else f"{numeric:.1f}"

    def _safe_get(self, obj: Any, attr: str, default: Any = None) -> Any:
        if obj is None:
            return default
        try:
            value = getattr(obj, attr)
        except Exception:
            return default
        return default if value is None else value

    def _count_report_pages(self, html: str) -> int:
        return max(1, len(re.findall(r'data-report-page="', html)))

    def _assert_offline_html(self, html: str) -> None:
        if re.search(r"""(?:https?:)?//""", html, flags=re.IGNORECASE):
            raise ValueError("PDF templates must be offline-only: external URLs are forbidden.")
