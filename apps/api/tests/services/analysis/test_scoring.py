from services.analysis.scoring import InMemorySectorWeightsRepository, ScoringEngine
from services.schemas import ESRSRequirement, ExtractedESRSData


def make_requirement(code: str, obligatoire: bool = True) -> ESRSRequirement:
    return ESRSRequirement(
        code_esrs=code.split("-")[0],
        identifiant=code,
        intitule=f"Requirement {code}",
        obligatoire=obligatoire,
    )


def test_mandatory_missing_scores_zero() -> None:
    engine = ScoringEngine(InMemorySectorWeightsRepository())

    score = engine.calculate_esrs_score(make_requirement("E1-6"), None, "27.1")

    assert score.score == 0
    assert score.status == "missing"
    assert "missing_mandatory_requirement" in score.penalties


def test_optional_missing_is_not_penalized() -> None:
    engine = ScoringEngine(InMemorySectorWeightsRepository())

    score = engine.calculate_esrs_score(make_requirement("E4-1", obligatoire=False), None, "27.1")

    assert score.score is None
    assert score.status == "na"
    assert score.penalties == []


def test_high_confidence_present_scores_audit_ready_range() -> None:
    engine = ScoringEngine(InMemorySectorWeightsRepository())
    extracted = ExtractedESRSData(
        esrs_code="E1-1",
        present=True,
        value="Plan de transition documente",
        page_source=12,
        confidence=0.92,
    )

    score = engine.calculate_esrs_score(make_requirement("E1-1"), extracted, "27.1")

    assert score.score is not None
    assert score.score >= 80
    assert score.status == "complete"
    assert "high_confidence_extraction" in score.bonuses
    assert "source_page_available" in score.bonuses


def test_low_confidence_present_scores_partial_range() -> None:
    engine = ScoringEngine(InMemorySectorWeightsRepository())
    extracted = ExtractedESRSData(
        esrs_code="S1-6",
        present=True,
        value="Effectifs mentionnes sans detail",
        confidence=0.42,
    )

    score = engine.calculate_esrs_score(make_requirement("S1-6"), extracted, "27.1")

    assert score.score is not None
    assert 20 <= score.score <= 50
    assert score.status == "partial"
    assert "low_confidence_extraction" in score.penalties


def test_global_score_uses_sector_weights_and_adjustments() -> None:
    engine = ScoringEngine(
        InMemorySectorWeightsRepository(
            {
                "27.1": {
                    "E1-1": 2.0,
                    "S1-6": 1.0,
                }
            }
        )
    )

    scores = [
        engine.calculate_esrs_score(
            make_requirement("E1-1"),
            ExtractedESRSData(
                esrs_code="E1-1",
                present=True,
                value="OK",
                page_source=4,
                confidence=0.9,
            ),
            "27.1",
        ),
        engine.calculate_esrs_score(
            make_requirement("S1-6"),
            ExtractedESRSData(
                esrs_code="S1-6",
                present=True,
                value="Partiel",
                confidence=0.45,
            ),
            "27.1",
        ),
    ]

    global_score = engine.calculate_global_score(scores)

    assert global_score.raw_score > 50
    assert 0 <= global_score.adjusted_score <= 100
    assert global_score.coverage_ratio == 1
    assert len(global_score.details) == 2

