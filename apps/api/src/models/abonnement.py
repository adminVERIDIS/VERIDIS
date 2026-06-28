from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .entities import Entreprise


class PlanType(str, Enum):
    ESSENTIAL = "essential"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    FREE = "free"


class SubscriptionStatus(str, Enum):
    TRIAL_ACTIVE = "trial_active"
    TRIAL_EXPIRED = "trial_expired"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    READ_ONLY = "read_only"


class Interval(str, Enum):
    MONTH = "month"
    YEAR = "year"


class WebhookEventStatus(str, Enum):
    RECEIVED = "received"
    PROCESSED = "processed"
    FAILED = "failed"


class Abonnement(Base, TimestampMixin):
    """
    Source de verite locale pour les acces premium VERIDIS.

    Stripe reste la source billing, mais l'API lit ce modele a chaque requete
    protegee pour eviter un appel reseau au moment du controle d'acces.
    """

    __tablename__ = "abonnements"
    __table_args__ = (
        UniqueConstraint("stripe_subscription_id", name="uq_abonnements_stripe_subscription"),
        Index("ix_abonnements_entreprise_status", "entreprise_id", "status"),
        Index("ix_abonnements_stripe_customer", "stripe_customer_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entreprise_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entreprises.id", ondelete="RESTRICT"),
        nullable=False,
    )
    stripe_customer_id: Mapped[str] = mapped_column(String(255), nullable=False)
    stripe_subscription_id: Mapped[str] = mapped_column(String(255), nullable=False)
    stripe_price_id: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[PlanType] = mapped_column(SQLEnum(PlanType, name="plan_type"), nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(
        SQLEnum(SubscriptionStatus, name="subscription_status"),
        nullable=False,
    )
    billing_interval: Mapped[Interval] = mapped_column(
        SQLEnum(Interval, name="billing_interval"),
        nullable=False,
    )
    trial_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cancel_at_period_end: Mapped[bool] = mapped_column(default=False, nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    max_rapports: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_utilisateurs: Mapped[int] = mapped_column(Integer, nullable=False)
    features: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    entreprise: Mapped[Entreprise] = relationship(lazy="raise")


class StripeWebhookEvent(Base, TimestampMixin):
    """Journal idempotent des events Stripe recus."""

    __tablename__ = "stripe_webhook_events"
    __table_args__ = (
        Index("ix_stripe_webhook_events_status", "status"),
        Index("ix_stripe_webhook_events_type_created", "event_type", "created_at"),
    )

    event_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[WebhookEventStatus] = mapped_column(
        SQLEnum(WebhookEventStatus, name="webhook_event_status"),
        nullable=False,
        default=WebhookEventStatus.RECEIVED,
    )
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
