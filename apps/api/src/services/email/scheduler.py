from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Protocol
from uuid import UUID


class EmailPriority(int, Enum):
    REGULATORY = 1
    ONBOARDING = 2
    RE_ENGAGEMENT = 3


class ScheduledEmailType(str, Enum):
    WELCOME_TRIAL = "welcome_trial"
    UPLOAD_REMINDER = "upload_reminder"
    SECTOR_BENCHMARK = "sector_benchmark"
    ANALYSIS_READY = "analysis_ready"
    TRIAL_EXPIRING = "trial_expiring"
    FINAL_CHANCE = "final_chance"
    TRIAL_ENDED = "trial_ended"
    REGULATORY_ALERT = "regulatory_alert"
    DEADLINE_ALERT = "deadline_alert"
    MONTHLY_BENCHMARK = "monthly_benchmark"
    RE_ENGAGEMENT = "re_engagement"


@dataclass(frozen=True)
class UserEmailProfile:
    user_id: UUID
    email: str
    prenom: str
    entreprise: str
    signup_at: datetime
    unsubscribe_url: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScheduledEmail:
    user_id: UUID
    email: str
    template: ScheduledEmailType
    scheduled_at: datetime
    priority: EmailPriority
    condition: str | None
    context: dict[str, Any]


class EmailQueueRepository(Protocol):
    async def queue_email(self, email: ScheduledEmail) -> None:
        ...

    async def cancel_pending_emails(self, user_id: UUID, reason: str) -> int:
        ...

    async def count_marketing_emails_since(self, user_id: UUID, since: datetime) -> int:
        ...

    async def regulatory_digest_recipients(self) -> list[UserEmailProfile]:
        ...


TRIAL_SEQUENCE = [
    (0, ScheduledEmailType.WELCOME_TRIAL, None),
    (2, ScheduledEmailType.UPLOAD_REMINDER, "document_not_uploaded"),
    (5, ScheduledEmailType.SECTOR_BENCHMARK, "document_uploaded_analysis_not_started"),
    (8, ScheduledEmailType.ANALYSIS_READY, "analysis_completed"),
    (11, ScheduledEmailType.TRIAL_EXPIRING, None),
    (13, ScheduledEmailType.FINAL_CHANCE, None),
    (14, ScheduledEmailType.TRIAL_ENDED, "trial_not_converted"),
]


class EmailScheduler:
    """
    Ordonnanceur anti-spam pour onboarding, alertes et re-engagement.
    """

    def __init__(
        self,
        repository: EmailQueueRepository,
        *,
        marketing_cooldown: timedelta = timedelta(hours=48),
    ) -> None:
        self.repository = repository
        self.marketing_cooldown = marketing_cooldown

    async def schedule_onboarding_sequence(self, user: UserEmailProfile) -> list[ScheduledEmail]:
        scheduled: list[ScheduledEmail] = []
        for day_offset, template, condition in TRIAL_SEQUENCE:
            email = ScheduledEmail(
                user_id=user.user_id,
                email=user.email,
                template=template,
                scheduled_at=user.signup_at + timedelta(days=day_offset),
                priority=EmailPriority.ONBOARDING,
                condition=condition,
                context=self._base_context(user),
            )
            await self.repository.queue_email(email)
            scheduled.append(email)
        return scheduled

    async def cancel_pending_emails(self, user: UserEmailProfile, reason: str) -> int:
        return await self.repository.cancel_pending_emails(user.user_id, reason)

    async def send_regulatory_digest(self) -> int:
        recipients = await self.repository.regulatory_digest_recipients()
        queued = 0
        for user in recipients:
            if await self._is_marketing_suppressed(user.user_id):
                continue
            email = ScheduledEmail(
                user_id=user.user_id,
                email=user.email,
                template=ScheduledEmailType.REGULATORY_ALERT,
                scheduled_at=datetime.now(UTC),
                priority=EmailPriority.REGULATORY,
                condition="active_customer",
                context={
                    **self._base_context(user),
                    "digest_type": "monthly_regulatory",
                },
            )
            await self.repository.queue_email(email)
            queued += 1
        return queued

    async def schedule_deadline_alerts(
        self,
        user: UserEmailProfile,
        deadline: datetime,
    ) -> list[ScheduledEmail]:
        offsets = [90, 60, 30, 14, 7, 1]
        scheduled: list[ScheduledEmail] = []
        for days_before in offsets:
            email = ScheduledEmail(
                user_id=user.user_id,
                email=user.email,
                template=ScheduledEmailType.DEADLINE_ALERT,
                scheduled_at=deadline - timedelta(days=days_before),
                priority=EmailPriority.REGULATORY,
                condition=f"deadline_j_minus_{days_before}",
                context={
                    **self._base_context(user),
                    "deadline": deadline.date().isoformat(),
                    "jours_restant": days_before,
                },
            )
            await self.repository.queue_email(email)
            scheduled.append(email)
        return scheduled

    async def schedule_re_engagement(self, user: UserEmailProfile, churned_at: datetime) -> list[ScheduledEmail]:
        scheduled: list[ScheduledEmail] = []
        for day_offset in (30, 90, 180):
            email = ScheduledEmail(
                user_id=user.user_id,
                email=user.email,
                template=ScheduledEmailType.RE_ENGAGEMENT,
                scheduled_at=churned_at + timedelta(days=day_offset),
                priority=EmailPriority.RE_ENGAGEMENT,
                condition=f"churn_j_plus_{day_offset}",
                context={**self._base_context(user), "inactive_days": day_offset},
            )
            await self.repository.queue_email(email)
            scheduled.append(email)
        return scheduled

    async def _is_marketing_suppressed(self, user_id: UUID) -> bool:
        since = datetime.now(UTC) - self.marketing_cooldown
        count = await self.repository.count_marketing_emails_since(user_id, since)
        return count >= 1

    def _base_context(self, user: UserEmailProfile) -> dict[str, Any]:
        return {
            "prenom": user.prenom,
            "entreprise": user.entreprise,
            "unsubscribe_url": user.unsubscribe_url,
            **user.properties,
        }
