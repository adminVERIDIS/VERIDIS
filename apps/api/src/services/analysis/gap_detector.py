from __future__ import annotations

import logging
import re
from typing import Any

from services.schemas import (
    EntrepriseContext,
    ExtractedESRSData,
    Gap,
    GapCategory,
    GapRule,
    Severity,
)

logger = logging.getLogger(__name__)


SEVERITY_ORDER = {
    Severity.CRITIQUE: 4,
    Severity.MAJEUR: 3,
    Severity.MINEUR: 2,
    Severity.INFO: 1,
}


class GapDetector:
    """
    Detects CSRD gaps with explicit versioned rules and lightweight heuristics.
    """

    RULES: list[GapRule] = [
        GapRule(
            id="GAP-E1-MISSING-SCOPE3",
            condition="E1-1.present AND NOT E1-6.present",
            severity=Severity.CRITIQUE,
            category=GapCategory.DONNEE_MANQUANTE,
            message_template=(
                "Vous declarez {scope1_2_value} d'emissions directes (Scope 1+2) "
                "mais ne mentionnez pas votre Scope 3. Dans le secteur {sector}, "
                "le Scope 3 represente souvent la majorite des emissions."
            ),
            action_template=(
                "1. Identifier les categories Scope 3 pertinentes\n"
                "2. Collecter les donnees fournisseurs\n"
                "3. Calculer selon GHG Protocol\n"
                "4. Documenter la methode dans le rapport"
            ),
            deadline_days=90,
            resources=["guide-scope3-ghg-protocol", "template-fournisseurs"],
            impact_score=95,
        ),
        GapRule(
            id="GAP-E1-MISSING-TRANSITION-PLAN",
            condition="NOT E1-1.present",
            severity=Severity.CRITIQUE,
            category=GapCategory.DONNEE_MANQUANTE,
            message_template="Le plan de transition climat E1-1 n'est pas documente pour {sector}.",
            action_template="Formaliser objectifs, leviers, CAPEX/OPEX et gouvernance climat.",
            deadline_days=120,
            resources=["template-plan-transition"],
            impact_score=92,
        ),
        GapRule(
            id="GAP-E1-MISSING-ENERGY",
            condition="NOT E1-5.present",
            severity=Severity.MAJEUR,
            category=GapCategory.DONNEE_MANQUANTE,
            message_template="La consommation d'energie E1-5 est absente.",
            action_template="Collecter les consommations par source et periode.",
            deadline_days=60,
            resources=["template-energie"],
            impact_score=75,
        ),
        GapRule(
            id="GAP-E2-MISSING-POLLUTION",
            condition="NOT E2-1.present",
            severity=Severity.MAJEUR,
            category=GapCategory.METHODOLOGIE,
            message_template="Les politiques pollution E2-1 ne sont pas identifiees.",
            action_template="Documenter politiques, controles et rejets significatifs.",
            deadline_days=90,
            resources=["guide-esrs-e2"],
            impact_score=68,
        ),
        GapRule(
            id="GAP-E3-MISSING-WATER",
            condition="NOT E3-4.present",
            severity=Severity.MAJEUR,
            category=GapCategory.DONNEE_MANQUANTE,
            message_template="Les donnees eau E3-4 sont absentes.",
            action_template="Collecter prelevements, consommations et zones de stress hydrique.",
            deadline_days=90,
            resources=["template-eau"],
            impact_score=65,
        ),
        GapRule(
            id="GAP-E4-MISSING-BIODIVERSITY",
            condition="NOT E4-1.present",
            severity=Severity.MINEUR,
            category=GapCategory.METHODOLOGIE,
            message_template="La transition biodiversite E4-1 n'est pas documentee.",
            action_template="Verifier materialite biodiversite et documenter l'analyse.",
            deadline_days=120,
            resources=["guide-esrs-e4"],
            impact_score=45,
        ),
        GapRule(
            id="GAP-E5-MISSING-CIRCULARITY",
            condition="NOT E5-5.present",
            severity=Severity.MINEUR,
            category=GapCategory.DONNEE_MANQUANTE,
            message_template="Les flux de ressources E5-5 ne sont pas quantifies.",
            action_template="Quantifier entrees, sorties, dechets et taux de recyclage.",
            deadline_days=120,
            resources=["template-economie-circulaire"],
            impact_score=48,
        ),
        GapRule(
            id="GAP-S1-MISSING-WORKFORCE",
            condition="NOT S1-6.present",
            severity=Severity.CRITIQUE,
            category=GapCategory.DONNEE_MANQUANTE,
            message_template="Les effectifs S1-6 ne sont pas presentes.",
            action_template="Exporter effectifs par contrat, genre, pays et categorie.",
            deadline_days=45,
            resources=["template-effectifs"],
            impact_score=88,
        ),
        GapRule(
            id="GAP-S1-MISSING-SAFETY",
            condition="NOT S1-14.present",
            severity=Severity.MAJEUR,
            category=GapCategory.DONNEE_MANQUANTE,
            message_template="Les indicateurs sante-securite S1-14 sont absents.",
            action_template="Collecter accidents, taux de frequence, gravite et couverture SMS.",
            deadline_days=75,
            resources=["template-securite"],
            impact_score=72,
        ),
        GapRule(
            id="GAP-S1-MISSING-PAY-GAP",
            condition="NOT S1-16.present",
            severity=Severity.MAJEUR,
            category=GapCategory.DONNEE_MANQUANTE,
            message_template="Les ecarts de remuneration S1-16 ne sont pas publies.",
            action_template="Calculer ecart salarial et ratio remuneration totale.",
            deadline_days=90,
            resources=["template-remuneration"],
            impact_score=70,
        ),
        GapRule(
            id="GAP-S2-MISSING-WORKERS-VALUE-CHAIN",
            condition="NOT S2-1.present",
            severity=Severity.MAJEUR,
            category=GapCategory.METHODOLOGIE,
            message_template="Les politiques travailleurs de la chaine de valeur S2-1 sont absentes.",
            action_template="Cartographier risques fournisseurs et politiques associees.",
            deadline_days=120,
            resources=["guide-esrs-s2"],
            impact_score=66,
        ),
        GapRule(
            id="GAP-S3-MISSING-COMMUNITIES",
            condition="NOT S3-1.present",
            severity=Severity.MINEUR,
            category=GapCategory.METHODOLOGIE,
            message_template="Les communautes affectees S3-1 ne sont pas documentees.",
            action_template="Verifier materialite et documenter consultations locales.",
            deadline_days=120,
            resources=["guide-esrs-s3"],
            impact_score=42,
        ),
        GapRule(
            id="GAP-S4-MISSING-CONSUMERS",
            condition="NOT S4-1.present",
            severity=Severity.MINEUR,
            category=GapCategory.METHODOLOGIE,
            message_template="Les politiques consommateurs S4-1 ne sont pas documentees.",
            action_template="Formaliser politiques securite, information et protection clients.",
            deadline_days=120,
            resources=["guide-esrs-s4"],
            impact_score=44,
        ),
        GapRule(
            id="GAP-G1-MISSING-BUSINESS-CONDUCT",
            condition="NOT G1-1.present",
            severity=Severity.MAJEUR,
            category=GapCategory.METHODOLOGIE,
            message_template="La conduite des affaires G1-1 n'est pas decrite.",
            action_template="Documenter code de conduite, alertes internes et controles anticorruption.",
            deadline_days=90,
            resources=["guide-esrs-g1"],
            impact_score=62,
        ),
        GapRule(
            id="GAP-G1-MISSING-PAYMENT-PRACTICES",
            condition="NOT G1-6.present",
            severity=Severity.MINEUR,
            category=GapCategory.DONNEE_MANQUANTE,
            message_template="Les pratiques de paiement G1-6 sont absentes.",
            action_template="Calculer delais de paiement moyens et litiges fournisseurs.",
            deadline_days=90,
            resources=["template-paiements"],
            impact_score=38,
        ),
        GapRule(
            id="GAP-ESRS2-MISSING-GOVERNANCE",
            condition="NOT GOV-1.present",
            severity=Severity.CRITIQUE,
            category=GapCategory.METHODOLOGIE,
            message_template="La gouvernance durabilite GOV-1 n'est pas documentee.",
            action_template="Identifier organes responsables, competences et frequence de revue.",
            deadline_days=60,
            resources=["template-gouvernance"],
            impact_score=86,
        ),
        GapRule(
            id="GAP-ESRS2-MISSING-IRO",
            condition="NOT IRO-1.present",
            severity=Severity.CRITIQUE,
            category=GapCategory.METHODOLOGIE,
            message_template="Le processus d'identification IRO-1 n'est pas documente.",
            action_template="Documenter impacts, risques, opportunites et double materialite.",
            deadline_days=75,
            resources=["template-double-materialite"],
            impact_score=90,
        ),
        GapRule(
            id="GAP-ESRS2-MISSING-METRICS",
            condition="NOT MDR-M.present",
            severity=Severity.MAJEUR,
            category=GapCategory.TRACABILITE,
            message_template="Les metriques MDR-M ne sont pas reliees aux politiques et actions.",
            action_template="Relier chaque metrique a une source, un owner et une methode.",
            deadline_days=60,
            resources=["template-mdr"],
            impact_score=64,
        ),
        GapRule(
            id="GAP-LOW-CONFIDENCE-E1-6",
            condition="E1-6.present",
            severity=Severity.MAJEUR,
            category=GapCategory.DONNEE_PARTIELLE,
            message_template="Le Scope 3 E1-6 est present mais doit etre controle si la confiance est faible.",
            action_template="Verifier categories incluses, facteurs d'emission et limites organisationnelles.",
            deadline_days=60,
            resources=["checklist-scope3"],
            impact_score=60,
        ),
        GapRule(
            id="GAP-TRACEABILITY-SOURCES",
            condition="GOV-5.present",
            severity=Severity.INFO,
            category=GapCategory.TRACABILITE,
            message_template="Les controles internes GOV-5 doivent rester relies aux preuves sources.",
            action_template="Conserver piece, owner, date de controle et version de methode.",
            deadline_days=30,
            resources=["checklist-audit-trail"],
            impact_score=25,
        ),
    ]

    def detect_gaps(
        self,
        extractions: list[ExtractedESRSData],
        entreprise: EntrepriseContext,
    ) -> list[Gap]:
        context = build_context(extractions)
        context["sector"] = entreprise.secteur_naf
        gaps: list[Gap] = []
        seen: set[str] = set()

        for rule in self.RULES:
            gap = self._apply_rule(rule, context)
            if gap and gap.id not in seen:
                gaps.append(gap)
                seen.add(gap.id)

        for extraction in extractions:
            for gap in self._detect_sector_anomalies(extraction, entreprise.secteur_naf):
                if gap.id not in seen:
                    gaps.append(gap)
                    seen.add(gap.id)

            if extraction.present and extraction.confidence < 0.5:
                gap = Gap(
                    id=f"GAP-LOW-CONFIDENCE-{normalize_code(extraction.esrs_code)}",
                    requirement_code=extraction.esrs_code,
                    severity=Severity.MAJEUR,
                    category=GapCategory.DONNEE_PARTIELLE,
                    description=(
                        f"La donnee {extraction.esrs_code} est detectee avec une confiance "
                        f"faible ({extraction.confidence:.0%})."
                    ),
                    impact_score=55,
                    action_required="Verifier la source, ajouter une page de preuve et documenter la methode.",
                    deadline_days=45,
                    resources=["checklist-preuves"],
                    confidence=0.8,
                )
                if gap.id not in seen:
                    gaps.append(gap)
                    seen.add(gap.id)

        return sorted(
            gaps,
            key=lambda gap: (
                -SEVERITY_ORDER[gap.severity],
                -gap.impact_score,
                gap.deadline_days,
                gap.id,
            ),
        )

    def _apply_rule(self, rule: GapRule, context: dict[str, Any]) -> Gap | None:
        try:
            matches = evaluate_condition(rule.condition, context)
        except ValueError as exc:
            logger.warning("Invalid gap rule %s: %s", rule.id, exc)
            return None

        if not matches:
            return None

        if rule.id == "GAP-LOW-CONFIDENCE-E1-6":
            extraction = context.get("E1-6")
            if not isinstance(extraction, ExtractedESRSData) or extraction.confidence >= 0.7:
                return None

        if rule.id == "GAP-TRACEABILITY-SOURCES":
            extraction = context.get("GOV-5")
            if not isinstance(extraction, ExtractedESRSData) or extraction.page_source is not None:
                return None

        message = rule.message_template.format(
            sector=context.get("sector", "unknown"),
            scope1_2_value=get_value(context.get("E1-1")),
        )

        return Gap(
            id=rule.id,
            requirement_code=extract_primary_code(rule.condition),
            severity=rule.severity,
            category=rule.category,
            description=message,
            impact_score=rule.impact_score,
            action_required=rule.action_template,
            deadline_days=rule.deadline_days,
            resources=rule.resources,
            confidence=0.95,
        )

    def _detect_sector_anomalies(
        self,
        extraction: ExtractedESRSData,
        sector: str,
    ) -> list[Gap]:
        numeric_value = coerce_number(extraction.value)
        if numeric_value is None:
            return []

        benchmark = SECTOR_BENCHMARKS.get(sector, {}).get(extraction.esrs_code)
        if benchmark is None:
            return []

        median, max_reasonable = benchmark
        if numeric_value <= max_reasonable:
            return []

        return [
            Gap(
                id=f"GAP-SECTOR-ANOMALY-{normalize_code(extraction.esrs_code)}",
                requirement_code=extraction.esrs_code,
                severity=Severity.MAJEUR,
                category=GapCategory.INCOHERENCE,
                description=(
                    f"La valeur {numeric_value:g} pour {extraction.esrs_code} depasse le seuil "
                    f"sectoriel attendu ({max_reasonable:g}; mediane {median:g})."
                ),
                impact_score=70,
                action_required="Verifier unite, perimetre, facteur de conversion et source documentaire.",
                deadline_days=30,
                resources=["checklist-controle-coherence"],
                confidence=0.75,
            )
        ]


SECTOR_BENCHMARKS: dict[str, dict[str, tuple[float, float]]] = {
    "27.1": {
        "E1-6": (8.5, 42.5),
        "E1-5": (120.0, 600.0),
    },
    "unknown": {},
}


def build_context(extractions: list[ExtractedESRSData]) -> dict[str, Any]:
    return {extraction.esrs_code: extraction for extraction in extractions}


def evaluate_condition(condition: str, context: dict[str, Any]) -> bool:
    tokens = condition.split()
    if not tokens:
        raise ValueError("empty condition")

    def read_atom(token: str) -> bool:
        if not token.endswith(".present"):
            raise ValueError(f"unsupported atom '{token}'")
        code = token.removesuffix(".present")
        extraction = context.get(code)
        return bool(isinstance(extraction, ExtractedESRSData) and extraction.present)

    values: list[bool | str] = []
    negate_next = False
    for token in tokens:
        upper = token.upper()
        if upper == "NOT":
            negate_next = True
            continue
        if upper in {"AND", "OR"}:
            values.append(upper)
            continue

        atom = read_atom(token)
        values.append(not atom if negate_next else atom)
        negate_next = False

    result = bool(values[0])
    index = 1
    while index < len(values):
        operator = values[index]
        operand = bool(values[index + 1])
        if operator == "AND":
            result = result and operand
        elif operator == "OR":
            result = result or operand
        else:
            raise ValueError(f"unsupported operator '{operator}'")
        index += 2

    return result


def extract_primary_code(condition: str) -> str | None:
    match = re.search(r"([A-Z0-9]+-\d+|GOV-\d+|IRO-\d+|MDR-[A-Z])\.present", condition)
    return match.group(1) if match else None


def get_value(value: Any) -> str:
    if isinstance(value, ExtractedESRSData) and value.value is not None:
        unit = f" {value.value_unit}" if value.value_unit else ""
        return f"{value.value}{unit}"
    return "des donnees"


def coerce_number(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace(",", ".").replace(" ", "")
        match = re.search(r"-?\d+(\.\d+)?", cleaned)
        if match:
            return float(match.group(0))
    return None


def normalize_code(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").upper()

