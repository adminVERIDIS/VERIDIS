from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, SoftDeleteMixin, TimestampMixin


class Entreprise(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "entreprises"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    siren: Mapped[str] = mapped_column(String(9), unique=True, nullable=False, index=True)
    raison_sociale: Mapped[str] = mapped_column(String(255), nullable=False)
    effectif: Mapped[int | None] = mapped_column(Integer, nullable=True)
    secteur_naf: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    date_premiere_obligation: Mapped[date | None] = mapped_column(Date, nullable=True)
    statut_conformite: Mapped[str] = mapped_column(String(32), default="non_evalue", nullable=False)

    rapports: Mapped[list[RapportCSRD]] = relationship(
        back_populates="entreprise",
        cascade="save-update, merge",
        lazy="raise",
    )


class RapportCSRD(Base, TimestampMixin):
    __tablename__ = "rapports_csrd"
    __table_args__ = (
        UniqueConstraint("entreprise_id", "exercice", name="uq_rapport_csrd_entreprise_exercice"),
        Index("ix_rapports_csrd_entreprise_exercice", "entreprise_id", "exercice"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entreprise_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entreprises.id", ondelete="RESTRICT"),
        nullable=False,
    )
    exercice: Mapped[int] = mapped_column(Integer, nullable=False)
    statut: Mapped[str] = mapped_column(String(32), default="uploaded", nullable=False)
    score_global: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    date_echeance: Mapped[date | None] = mapped_column(Date, nullable=True)
    fichier_source: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    entreprise: Mapped[Entreprise] = relationship(back_populates="rapports", lazy="raise")
    reponses: Mapped[list[ReponseESRS]] = relationship(
        back_populates="rapport",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    gaps: Mapped[list[GapAnalysis]] = relationship(
        back_populates="rapport",
        cascade="all, delete-orphan",
        lazy="raise",
    )


class ESRSRequirement(Base, TimestampMixin):
    __tablename__ = "esrs_requirements"
    __table_args__ = (
        UniqueConstraint("code_esrs", "identifiant", name="uq_esrs_requirement_code_identifiant"),
        Index("ix_esrs_requirements_code", "code_esrs"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code_esrs: Mapped[str] = mapped_column(String(16), nullable=False)
    identifiant: Mapped[str] = mapped_column(String(64), nullable=False)
    intitule: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    type_donnee: Mapped[str] = mapped_column(String(64), nullable=False)
    obligatoire: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    guide_remplissage: Mapped[str | None] = mapped_column(Text, nullable=True)
    exemple_conforme: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    reponses: Mapped[list[ReponseESRS]] = relationship(back_populates="requirement", lazy="raise")


class ReponseESRS(Base, TimestampMixin):
    __tablename__ = "reponses_esrs"
    __table_args__ = (
        UniqueConstraint("rapport_id", "requirement_id", name="uq_reponse_esrs_rapport_requirement"),
        Index("ix_reponses_esrs_rapport_statut", "rapport_id", "statut"),
        Index("ix_reponses_esrs_requirement", "requirement_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rapport_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rapports_csrd.id", ondelete="CASCADE"),
        nullable=False,
    )
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("esrs_requirements.id", ondelete="RESTRICT"),
        nullable=False,
    )
    statut: Mapped[str] = mapped_column(String(32), default="manquant", nullable=False)
    donnee_fournie: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    source_document: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    confiance_extraction: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)

    rapport: Mapped[RapportCSRD] = relationship(back_populates="reponses", lazy="raise")
    requirement: Mapped[ESRSRequirement] = relationship(back_populates="reponses", lazy="raise")


class GapAnalysis(Base, TimestampMixin):
    __tablename__ = "gap_analysis"
    __table_args__ = (
        Index("ix_gap_analysis_rapport_severite", "rapport_id", "severite"),
        Index("ix_gap_analysis_resolution", "statut_resolution"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rapport_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rapports_csrd.id", ondelete="CASCADE"),
        nullable=False,
    )
    type_gap: Mapped[str] = mapped_column(String(64), nullable=False)
    severite: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    impact_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    action_requise: Mapped[str] = mapped_column(Text, nullable=False)
    delai_recommande: Mapped[int] = mapped_column(Integer, nullable=False)
    ressources_aide: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    statut_resolution: Mapped[str] = mapped_column(String(32), default="ouvert", nullable=False)

    rapport: Mapped[RapportCSRD] = relationship(back_populates="gaps", lazy="raise")

