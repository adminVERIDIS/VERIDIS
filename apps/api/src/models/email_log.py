from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import DateTime, Enum as SQLEnum, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, utc_now


class EmailStatus(str, Enum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    COMPLAINED = "complained"
    CANCELLED = "cancelled"
    FAILED = "failed"


class EmailChannel(str, Enum):
    TRANSACTIONAL = "transactional"
    MARKETING = "marketing"
    REGULATORY = "regulatory"


class EmailLog(Base, TimestampMixin):
    """Audit complet des emails envoyes pour RGPD, support et debug."""

    __tablename__ = "email_logs"
    __table_args__ = (
        Index("ix_email_logs_recipient_status", "recipient", "status"),
        Index("ix_email_logs_template_created", "template", "created_at"),
        Index("ix_email_logs_channel_sent", "channel", "sent_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipient: Mapped[str] = mapped_column(String(320), nullable=False)
    template: Mapped[str] = mapped_column(String(128), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[EmailStatus] = mapped_column(
        SQLEnum(EmailStatus, name="email_status"),
        default=EmailStatus.QUEUED,
        nullable=False,
    )
    channel: Mapped[EmailChannel] = mapped_column(
        SQLEnum(EmailChannel, name="email_channel"),
        default=EmailChannel.TRANSACTIONAL,
        nullable=False,
    )
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    email_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
