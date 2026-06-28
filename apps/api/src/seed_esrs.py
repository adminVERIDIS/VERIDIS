from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import ESRSRequirement


class SeedValidationError(ValueError):
    """Raised when the ESRS reference package is inconsistent."""


@dataclass(frozen=True)
class SeedResult:
    created: int
    updated: int
    ignored: int
    total: int


Reference = dict[str, Any]

REQUIRED_STANDARD_KEYS = {
    "esrs_code",
    "esrs_name",
    "version",
    "requirement_count",
    "requirements",
}

REQUIRED_REQUIREMENT_KEYS = {
    "id",
    "code",
    "obligation",
    "intitule",
    "description_simple",
    "donnees_attendues",
    "guide_remplissage",
    "verification",
    "esrs_liees",
}


def load_esrs_reference(data_dir: Path) -> Reference:
    index_path = data_dir / "index.json"
    if not index_path.exists():
        raise SeedValidationError(f"Missing ESRS index: {index_path}")

    index = _read_json(index_path)
    standards: dict[str, dict[str, Any]] = {}
    for entry in index.get("esrs", []):
        filename = entry.get("file")
        if filename is None:
            continue
        if not isinstance(filename, str):
            raise SeedValidationError(f"Invalid file value for {entry!r}")

        standard = _read_json(data_dir / filename)
        code = standard.get("esrs_code")
        if not isinstance(code, str):
            raise SeedValidationError(f"Missing esrs_code in {filename}")
        standards[code] = standard

    reference = {"index": index, "standards": standards}
    validate_reference(reference)
    return reference


def validate_reference(reference: Reference) -> None:
    index = reference["index"]
    standards: dict[str, dict[str, Any]] = reference["standards"]
    index_version = _required_str(index, "version")
    declared_total = _required_int(index, "total_requirements")
    seen_codes: set[str] = set()
    generated_total = 0

    for entry in index.get("esrs", []):
        filename = entry.get("file")
        if filename is None:
            continue

        code = _required_str(entry, "code")
        standard = standards.get(code)
        if standard is None:
            raise SeedValidationError(f"Index references missing standard {code}")
        missing_keys = REQUIRED_STANDARD_KEYS - standard.keys()
        if missing_keys:
            raise SeedValidationError(f"{code} missing keys: {sorted(missing_keys)}")
        if standard["version"] != index_version:
            raise SeedValidationError(f"{code} version differs from index")
        if standard["requirement_count"] != len(standard["requirements"]):
            raise SeedValidationError(f"{code} requirement_count mismatch")

        for requirement in standard["requirements"]:
            missing_requirement_keys = REQUIRED_REQUIREMENT_KEYS - requirement.keys()
            if missing_requirement_keys:
                raise SeedValidationError(
                    f"{code} requirement missing keys: {sorted(missing_requirement_keys)}"
                )
            req_code = _required_str(requirement, "code")
            if req_code != requirement["id"]:
                raise SeedValidationError(f"{req_code} id/code mismatch")
            if req_code in seen_codes:
                raise SeedValidationError(f"Duplicate ESRS requirement code: {req_code}")
            seen_codes.add(req_code)
            generated_total += 1

    if generated_total != declared_total:
        raise SeedValidationError(
            f"Index total_requirements={declared_total} but generated={generated_total}"
        )

    for standard in standards.values():
        for requirement in standard["requirements"]:
            for linked_code in requirement["esrs_liees"]:
                if linked_code not in seen_codes:
                    raise SeedValidationError(
                        f"{requirement['code']} references unknown requirement {linked_code}"
                    )


def iter_requirement_payloads(reference: Reference) -> Iterable[tuple[dict[str, Any], dict[str, Any]]]:
    order = [
        entry["code"]
        for entry in reference["index"].get("esrs", [])
        if isinstance(entry.get("file"), str)
    ]
    for code in order:
        standard = reference["standards"][code]
        for requirement in standard["requirements"]:
            yield standard, requirement


def build_requirement_values(standard: dict[str, Any], requirement: dict[str, Any]) -> dict[str, Any]:
    guide_payload = {
        "donnees_attendues": requirement["donnees_attendues"],
        "guide_remplissage": requirement["guide_remplissage"],
        "verification": requirement["verification"],
        "esrs_liees": requirement["esrs_liees"],
        "source_reference": requirement.get("source_reference"),
        "critical_for_mvp": requirement.get("critical_for_mvp", False),
    }
    exemple = requirement["guide_remplissage"].get("exemple_conforme")
    return {
        "code_esrs": standard["esrs_code"],
        "identifiant": requirement["code"],
        "intitule": requirement["intitule"],
        "description": requirement["description_simple"],
        "type_donnee": requirement["donnees_attendues"]["format"],
        "obligatoire": requirement["obligation"] in {"mandatory", "mandatory_if_material"},
        "guide_remplissage": json.dumps(guide_payload, ensure_ascii=False, sort_keys=True),
        "exemple_conforme": {"texte": exemple} if exemple else None,
    }


async def seed_esrs(db: AsyncSession, data_dir: Path) -> SeedResult:
    reference = load_esrs_reference(data_dir)
    created = 0
    updated = 0
    ignored = 0

    for standard, requirement in iter_requirement_payloads(reference):
        values = build_requirement_values(standard, requirement)
        existing = await _find_existing_requirement(
            db,
            values["code_esrs"],
            values["identifiant"],
        )

        if existing is None:
            db.add(ESRSRequirement(**values))
            created += 1
            continue

        changed = _apply_updates(existing, values)
        if changed:
            updated += 1
        else:
            ignored += 1

    await db.flush()
    return SeedResult(
        created=created,
        updated=updated,
        ignored=ignored,
        total=created + updated + ignored,
    )


async def _find_existing_requirement(
    db: AsyncSession,
    code_esrs: str,
    identifiant: str,
) -> ESRSRequirement | None:
    result = await db.execute(
        select(ESRSRequirement).where(
            ESRSRequirement.code_esrs == code_esrs,
            ESRSRequirement.identifiant == identifiant,
        )
    )
    return result.scalar_one_or_none()


def _apply_updates(existing: ESRSRequirement, values: dict[str, Any]) -> bool:
    changed = False
    for key, value in values.items():
        if getattr(existing, key) != value:
            setattr(existing, key, value)
            changed = True
    return changed


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SeedValidationError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise SeedValidationError(f"JSON root must be an object: {path}")
    return payload


def _required_str(mapping: dict[str, Any], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise SeedValidationError(f"Missing string field: {key}")
    return value


def _required_int(mapping: dict[str, Any], key: str) -> int:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise SeedValidationError(f"Missing integer field: {key}")
    return value
