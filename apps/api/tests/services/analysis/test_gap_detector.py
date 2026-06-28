from services.analysis.gap_detector import GapDetector, evaluate_condition
from services.schemas import EntrepriseContext, ExtractedESRSData, GapCategory, Severity


def test_scope3_missing_rule_is_triggered_and_actionable() -> None:
    detector = GapDetector()
    entreprise = EntrepriseContext(raison_sociale="VERIDIS Test", secteur_naf="27.1")
    extractions = [
        ExtractedESRSData(
            esrs_code="E1-1",
            present=True,
            value="12450",
            value_unit="tCO2e",
            confidence=0.91,
        ),
        ExtractedESRSData(
            esrs_code="E1-6",
            present=False,
            confidence=0.2,
        ),
    ]

    gaps = detector.detect_gaps(extractions, entreprise)

    scope3_gap = next(gap for gap in gaps if gap.id == "GAP-E1-MISSING-SCOPE3")
    assert scope3_gap.severity == Severity.CRITIQUE
    assert scope3_gap.category == GapCategory.DONNEE_MANQUANTE
    assert "Scope 3" in scope3_gap.description
    assert scope3_gap.deadline_days == 90
    assert scope3_gap.resources


def test_low_confidence_gap_is_generated() -> None:
    detector = GapDetector()
    entreprise = EntrepriseContext(raison_sociale="VERIDIS Test", secteur_naf="27.1")

    gaps = detector.detect_gaps(
        [
            ExtractedESRSData(
                esrs_code="S1-6",
                present=True,
                value="effectif global",
                confidence=0.31,
            )
        ],
        entreprise,
    )

    assert any(gap.id == "GAP-LOW-CONFIDENCE-S1-6" for gap in gaps)


def test_sector_anomaly_detects_outlier() -> None:
    detector = GapDetector()
    entreprise = EntrepriseContext(raison_sociale="VERIDIS Test", secteur_naf="27.1")

    gaps = detector.detect_gaps(
        [
            ExtractedESRSData(
                esrs_code="E1-6",
                present=True,
                value="120",
                value_unit="tCO2e/M EUR",
                confidence=0.8,
            )
        ],
        entreprise,
    )

    assert any(gap.id == "GAP-SECTOR-ANOMALY-E1-6" for gap in gaps)


def test_gap_sorting_prioritizes_critical_high_impact() -> None:
    detector = GapDetector()
    entreprise = EntrepriseContext(raison_sociale="VERIDIS Test", secteur_naf="27.1")

    gaps = detector.detect_gaps(
        [
            ExtractedESRSData(esrs_code="E1-1", present=True, value="1000", confidence=0.9),
            ExtractedESRSData(esrs_code="E1-6", present=False, confidence=0.2),
            ExtractedESRSData(esrs_code="S1-6", present=False, confidence=0.1),
        ],
        entreprise,
    )

    assert gaps[0].severity == Severity.CRITIQUE
    assert gaps[0].impact_score >= gaps[1].impact_score


def test_condition_evaluator_supports_and_not() -> None:
    context = {
        "E1-1": ExtractedESRSData(esrs_code="E1-1", present=True, confidence=0.9),
        "E1-6": ExtractedESRSData(esrs_code="E1-6", present=False, confidence=0.2),
    }

    assert evaluate_condition("E1-1.present AND NOT E1-6.present", context) is True
    assert evaluate_condition("E1-1.present AND E1-6.present", context) is False

