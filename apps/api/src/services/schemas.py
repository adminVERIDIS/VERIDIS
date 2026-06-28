from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class Severity(str, Enum):
    CRITIQUE = "critique"
    MAJEUR = "majeur"
    MINEUR = "mineur"
    INFO = "info"


class GapCategory(str, Enum):
    DONNEE_MANQUANTE = "donnee_manquante"
    DONNEE_PARTIELLE = "donnee_partielle"
    INCOHERENCE = "incoherence"
    METHODOLOGIE = "methodologie"
    TRACABILITE = "tracabilite"


class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float


class DocumentChunk(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    content: str
    page_number: int | None = None
    section_title: str | None = None
    chunk_type: Literal["text", "table", "heading", "footer"] = "text"
    bbox: BoundingBox | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class DocumentMetadata(BaseModel):
    detected_company: str | None = None
    detected_year: int | None = None
    detected_frameworks: list[str] = Field(default_factory=list)
    language: str = "fr"
    word_count: int = 0


class ParsedDocument(BaseModel):
    filename: str
    file_type: Literal["pdf", "docx", "xlsx", "csv"]
    total_pages: int | None = None
    extracted_at: datetime
    chunks: list[DocumentChunk]
    metadata: DocumentMetadata


class DocumentClassification(BaseModel):
    framework: Literal["GRI", "SASB", "TCFD", "CSRD", "unknown"] = "unknown"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    language: str = "fr"
    notes: str = ""


class ESRSRequirement(BaseModel):
    id: UUID | None = None
    code_esrs: str
    identifiant: str
    intitule: str
    description: str = ""
    type_donnee: str = "texte"
    obligatoire: bool = True
    materiality_hint: str | None = None

    @property
    def full_code(self) -> str:
        return self.identifiant or self.code_esrs


class ExtractedESRSData(BaseModel):
    esrs_code: str
    present: bool
    value: str | float | int | None = None
    value_estimated: str | float | int | None = None
    value_unit: str | None = None
    page_source: int | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    notes: str = ""
    flags: list[str] = Field(default_factory=list)

    @field_validator("flags", mode="before")
    @classmethod
    def normalize_flags(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return list(value)


class GapDescription(BaseModel):
    title: str
    description: str
    action: str
    severity: Severity


class EntrepriseContext(BaseModel):
    id: UUID | None = None
    siren: str | None = None
    raison_sociale: str
    effectif: int | None = None
    secteur_naf: str = "unknown"


class ESRSScore(BaseModel):
    esrs_code: str
    score: float | None
    max_score: float = 100.0
    status: Literal["na", "missing", "partial", "complete"]
    weight: float
    confidence: float
    explanation: str
    penalties: list[str] = Field(default_factory=list)
    bonuses: list[str] = Field(default_factory=list)


class GlobalScore(BaseModel):
    raw_score: float
    adjusted_score: float
    percentile_sectoriel: float | None = None
    tendance: Literal["hausse", "stable", "baisse", "inconnue"] = "inconnue"
    coverage_ratio: float
    details: list[ESRSScore]


class GapRule(BaseModel):
    id: str
    condition: str
    severity: Severity
    category: GapCategory
    message_template: str
    action_template: str
    deadline_days: int
    resources: list[str] = Field(default_factory=list)
    impact_score: float = Field(default=50.0, ge=0.0, le=100.0)


class Gap(BaseModel):
    id: str
    requirement_code: str | None = None
    severity: Severity
    category: GapCategory
    description: str
    impact_score: float
    action_required: str
    deadline_days: int
    resources: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class AnalysisStep(BaseModel):
    name: str
    status: Literal["success", "failed", "skipped"]
    duration_ms: int
    error: str | None = None


class AnalysisResult(BaseModel):
    rapport_id: UUID
    status: Literal["success", "partial", "failed"]
    parsed_document: ParsedDocument | None = None
    classification: DocumentClassification | None = None
    extractions: list[ExtractedESRSData] = Field(default_factory=list)
    gaps: list[Gap] = Field(default_factory=list)
    score: GlobalScore | None = None
    steps: list[AnalysisStep] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
