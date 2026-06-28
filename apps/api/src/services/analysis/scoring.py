from __future__ import annotations

from typing import Protocol

from services.schemas import ESRSRequirement, ESRSScore, ExtractedESRSData, GlobalScore


class SectorWeightsRepository(Protocol):
    def get_weight(self, esrs_code: str, sector: str) -> float | None:
        raise NotImplementedError

    def get_percentile(self, score: float, sector: str) -> float | None:
        raise NotImplementedError


class InMemorySectorWeightsRepository:
    def __init__(self, weights: dict[str, dict[str, float]] | None = None):
        self._weights = weights or {}

    def get_weight(self, esrs_code: str, sector: str) -> float | None:
        sector_weights = self._weights.get(sector) or self._weights.get("default") or {}
        return sector_weights.get(esrs_code)

    def get_percentile(self, score: float, sector: str) -> float | None:
        if score >= 90:
            return 90.0
        if score >= 75:
            return 70.0
        if score >= 50:
            return 45.0
        return 20.0


class ScoringEngine:
    """
    Calculates CSRD conformity scores.

    Formula:
    Score_ESRS_i = valid_data_ratio * data_quality
    Global = weighted sum of ESRS scores adjusted for penalties and traceability.
    """

    def __init__(self, sector_weights: SectorWeightsRepository):
        self.weights = sector_weights

    def calculate_esrs_score(
        self,
        requirement: ESRSRequirement,
        extracted: ExtractedESRSData | None,
        sector: str,
    ) -> ESRSScore:
        weight = self._get_sector_weight(requirement.full_code, sector)

        if extracted is None or not extracted.present:
            if not requirement.obligatoire:
                return ESRSScore(
                    esrs_code=requirement.full_code,
                    score=None,
                    status="na",
                    weight=weight,
                    confidence=0.0,
                    explanation="Exigence optionnelle absente: non penalisee.",
                )
            return ESRSScore(
                esrs_code=requirement.full_code,
                score=0.0,
                status="missing",
                weight=weight,
                confidence=extracted.confidence if extracted else 0.0,
                explanation="Exigence obligatoire manquante: score 0.",
                penalties=["missing_mandatory_requirement"],
            )

        confidence = extracted.confidence
        penalties: list[str] = []
        bonuses: list[str] = []

        if confidence >= 0.8:
            base_score = 80 + (confidence - 0.8) * 100
            status = "complete"
            bonuses.append("high_confidence_extraction")
        elif confidence < 0.5:
            base_score = 20 + confidence * 60
            status = "partial"
            penalties.append("low_confidence_extraction")
        else:
            base_score = 50 + (confidence - 0.5) * 100
            status = "partial"

        if "non_conforme" in extracted.flags:
            base_score -= 25
            penalties.append("non_compliant_flag")
        if "estimation_sectorielle" in extracted.flags:
            base_score -= 10
            penalties.append("sector_estimate")
        if extracted.page_source is not None:
            base_score += 3
            bonuses.append("source_page_available")

        score = clamp(base_score, 0.0, 100.0)
        return ESRSScore(
            esrs_code=requirement.full_code,
            score=round(score, 2),
            status=status,  # type: ignore[arg-type]
            weight=weight,
            confidence=confidence,
            explanation=(
                f"Score calcule depuis presence={extracted.present}, "
                f"confiance={confidence:.2f}, flags={extracted.flags}."
            ),
            penalties=penalties,
            bonuses=bonuses,
        )

    def calculate_global_score(self, esrs_scores: list[ESRSScore]) -> GlobalScore:
        scored = [score for score in esrs_scores if score.score is not None]
        if not scored:
            return GlobalScore(
                raw_score=0.0,
                adjusted_score=0.0,
                percentile_sectoriel=None,
                coverage_ratio=0.0,
                details=esrs_scores,
            )

        total_weight = sum(max(score.weight, 0.0) for score in scored)
        if total_weight <= 0:
            total_weight = float(len(scored))
            weighted_sum = sum(score.score or 0.0 for score in scored)
        else:
            weighted_sum = sum((score.score or 0.0) * score.weight for score in scored)

        raw_score = weighted_sum / total_weight
        penalty_count = sum(len(score.penalties) for score in scored)
        bonus_count = sum(len(score.bonuses) for score in scored)
        adjustment = 1.0 - min(0.2, penalty_count * 0.015) + min(0.08, bonus_count * 0.005)
        adjusted = clamp(raw_score * adjustment, 0.0, 100.0)
        coverage_ratio = len([score for score in scored if (score.score or 0.0) > 0]) / len(scored)

        return GlobalScore(
            raw_score=round(raw_score, 2),
            adjusted_score=round(adjusted, 2),
            percentile_sectoriel=None,
            tendance="inconnue",
            coverage_ratio=round(coverage_ratio, 4),
            details=esrs_scores,
        )

    def _get_sector_weight(self, esrs_code: str, sector: str) -> float:
        weight = self.weights.get_weight(esrs_code, sector)
        if weight is None:
            weight = self.weights.get_weight(esrs_code.split("-")[0], sector)
        if weight is None:
            return 1.0
        return max(float(weight), 0.0)


def clamp(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, value))

