from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from services.pdf_generator import PDFRenderer
from services.schemas import (
    AnalysisResult,
    ESRSScore,
    ExtractedESRSData,
    Gap,
    GapCategory,
    GlobalScore,
    Severity,
)


class FakePage:
    def __init__(self) -> None:
        self.html = ""
        self.pdf_options: dict[str, object] = {}

    async def set_content(self, html: str, **kwargs: object) -> None:
        self.html = html

    async def pdf(self, **kwargs: object) -> bytes:
        self.pdf_options = kwargs
        return b"%PDF-1.4\n%VERIDIS\n"


class FakeBrowser:
    def __init__(self, page: FakePage) -> None:
        self.page = page
        self.closed = False

    async def new_page(self, **kwargs: object) -> FakePage:
        return self.page

    async def close(self) -> None:
        self.closed = True


class FakeChromium:
    def __init__(self, browser: FakeBrowser) -> None:
        self.browser = browser
        self.launch_options: dict[str, object] = {}

    async def launch(self, **kwargs: object) -> FakeBrowser:
        self.launch_options = kwargs
        return self.browser


class FakePlaywright:
    def __init__(self) -> None:
        self.page = FakePage()
        self.browser = FakeBrowser(self.page)
        self.chromium = FakeChromium(self.browser)


class FakeS3Client:
    def __init__(self) -> None:
        self.uploaded: dict[str, object] = {}

    async def upload_pdf(self, key: str, body: bytes, content_type: str) -> str:
        self.uploaded = {"key": key, "body": body, "content_type": content_type}
        return f"s3://veridis/{key}"


def rapport_fixture() -> SimpleNamespace:
    rapport_id = uuid4()
    return SimpleNamespace(
        id=rapport_id,
        exercice=2026,
        statut="analysed",
        score_global=68.5,
        date_echeance=date(2026, 12, 31),
        fichier_source={"filename": "rapport-durabilite.pdf"},
        entreprise=SimpleNamespace(
            raison_sociale="ACME Climate Industries",
            siren="123456789",
            secteur_naf="20.14Z",
            effectif=1240,
        ),
    )


def analysis_fixture(rapport_id) -> AnalysisResult:
    return AnalysisResult(
        rapport_id=rapport_id,
        status="success",
        extractions=[
            ExtractedESRSData(
                esrs_code="E1",
                present=True,
                value="Plan de transition climat publie",
                page_source=14,
                confidence=0.91,
            ),
            ExtractedESRSData(
                esrs_code="ESRS 2",
                present=True,
                value="Gouvernance ESG decrite",
                page_source=5,
                confidence=0.88,
            ),
        ],
        gaps=[
            Gap(
                id="gap-e1-transition",
                requirement_code="E1-1",
                severity=Severity.MAJEUR,
                category=GapCategory.DONNEE_PARTIELLE,
                description="Le plan de transition ne relie pas les objectifs aux CAPEX.",
                impact_score=76,
                action_required="Documenter les investissements alignes avec la trajectoire climat.",
                deadline_days=45,
                resources=["ESRS E1"],
                confidence=0.82,
            ),
            Gap(
                id="gap-esrs2-controls",
                requirement_code="ESRS 2 GOV-5",
                severity=Severity.CRITIQUE,
                category=GapCategory.TRACABILITE,
                description="La piste d'audit des controles ESG est incomplete.",
                impact_score=91,
                action_required="Formaliser les controles cles et leur proprietaire.",
                deadline_days=30,
                resources=["ESRS 2"],
                confidence=0.9,
            ),
        ],
        score=GlobalScore(
            raw_score=71,
            adjusted_score=68.5,
            percentile_sectoriel=62,
            tendance="stable",
            coverage_ratio=0.74,
            details=[
                ESRSScore(
                    esrs_code="E1",
                    score=66,
                    max_score=100,
                    status="partial",
                    weight=1.3,
                    confidence=0.86,
                    explanation="Les informations climat existent mais les preuves CAPEX restent partielles.",
                    penalties=["Lien CAPEX insuffisant"],
                    bonuses=["Objectifs de reduction identifies"],
                ),
                ESRSScore(
                    esrs_code="ESRS 2",
                    score=58,
                    max_score=100,
                    status="partial",
                    weight=1.2,
                    confidence=0.84,
                    explanation="La gouvernance est decrite mais les controles ne sont pas assez tracables.",
                    penalties=["Piste d'audit incomplete"],
                ),
            ],
        ),
    )


def test_rendered_html_contains_fixed_print_structure() -> None:
    rapport = rapport_fixture()
    renderer = PDFRenderer()

    html = renderer._inline_assets(renderer._render_html(rapport, analysis_fixture(rapport.id), "rapport_conformite.html"))

    assert html.count('data-report-page="') == 21
    assert "ACME Climate Industries" in html
    assert "Carte de chaleur des ecarts" in html
    assert "Changement climatique" in html
    assert "@page" in html
    assert "http://" not in html
    assert "https://" not in html


@pytest.mark.asyncio
async def test_generate_returns_pdf_document_and_upload_metadata() -> None:
    rapport = rapport_fixture()
    fake_playwright = FakePlaywright()
    fake_s3 = FakeS3Client()
    renderer = PDFRenderer(playwright=fake_playwright, s3_client=fake_s3)

    document = await renderer.generate(rapport, analysis_fixture(rapport.id))

    assert document.content.startswith(b"%PDF-1.4")
    assert document.page_count == 21
    assert document.file_size == len(document.content)
    assert len(document.checksum_sha256) == 64
    assert document.url == f"s3://veridis/{document.storage_key}"
    assert document.filename == "rapport-csrd-2026.pdf"
    assert fake_s3.uploaded["content_type"] == "application/pdf"
    assert fake_playwright.page.pdf_options["format"] == "A4"
    assert fake_playwright.page.pdf_options["print_background"] is True
    assert "Document confidentiel" in fake_playwright.page.html


def test_external_urls_are_rejected_before_pdf_rendering() -> None:
    renderer = PDFRenderer()

    with pytest.raises(ValueError, match="external URLs"):
        renderer._inline_assets('<img src="https://example.com/logo.png">')
