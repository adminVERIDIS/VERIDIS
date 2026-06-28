from __future__ import annotations

from pathlib import Path

import pytest

from seed_esrs import (
    SeedValidationError,
    build_requirement_values,
    iter_requirement_payloads,
    load_esrs_reference,
    validate_reference,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
DATA_DIR = REPO_ROOT / "packages" / "esrs-data"


def test_esrs_reference_loads_and_matches_declared_totals() -> None:
    reference = load_esrs_reference(DATA_DIR)
    requirements = list(iter_requirement_payloads(reference))

    assert reference["index"]["total_esrs"] == 12
    assert reference["index"]["total_requirements"] == 82
    assert len(requirements) == 82


def test_mvp_reference_counts_are_complete() -> None:
    reference = load_esrs_reference(DATA_DIR)
    standards = reference["standards"]

    assert standards["ESRS2"]["requirement_count"] == 12
    assert standards["E1"]["requirement_count"] == 9
    assert standards["S1"]["requirement_count"] == 17
    assert standards["G1"]["requirement_count"] == 6


def test_requirement_codes_are_unique_and_links_exist() -> None:
    reference = load_esrs_reference(DATA_DIR)
    codes = {
        requirement["code"]
        for _, requirement in iter_requirement_payloads(reference)
    }

    assert "E1-6" in codes
    assert "S1-14" in codes
    assert "G1-6" in codes
    assert "IRO-2" in codes


def test_requirement_values_match_esrs_requirement_model_shape() -> None:
    reference = load_esrs_reference(DATA_DIR)
    standard = reference["standards"]["E1"]
    requirement = standard["requirements"][5]

    values = build_requirement_values(standard, requirement)

    assert values["code_esrs"] == "E1"
    assert values["identifiant"] == "E1-6"
    assert values["obligatoire"] is True
    assert values["type_donnee"] == "tableau_tco2e"
    assert "verification" in values["guide_remplissage"]
    assert values["exemple_conforme"]["texte"].startswith("Pour E1-6")


def test_validation_rejects_broken_cross_reference() -> None:
    reference = load_esrs_reference(DATA_DIR)
    broken = {
        "index": reference["index"],
        "standards": {
            code: {
                **standard,
                "requirements": [dict(requirement) for requirement in standard["requirements"]],
            }
            for code, standard in reference["standards"].items()
        },
    }
    broken["standards"]["E1"]["requirements"][0]["esrs_liees"] = ["UNKNOWN-1"]

    with pytest.raises(SeedValidationError):
        validate_reference(broken)
