from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from services.email.scheduler import (
    EmailPriority,
    EmailScheduler,
    ScheduledEmail,
    ScheduledEmailType,
    UserEmailProfile,
)


class FakeEmailQueueRepository:
    def __init__(self, marketing_count: int = 0) -> None:
        self.queued: list[ScheduledEmail] = []
        self.cancelled: list[tuple[object, str]] = []
        self.marketing_count = marketing_count
        self.digest_recipients: list[UserEmailProfile] = []

    async def queue_email(self, email: ScheduledEmail) -> None:
        self.queued.append(email)

    async def cancel_pending_emails(self, user_id, reason: str) -> int:
        self.cancelled.append((user_id, reason))
        return 3

    async def count_marketing_emails_since(self, user_id, since: datetime) -> int:
        return self.marketing_count

    async def regulatory_digest_recipients(self) -> list[UserEmailProfile]:
        return self.digest_recipients


def user_profile() -> UserEmailProfile:
    return UserEmailProfile(
        user_id=uuid4(),
        email="anne@example.com",
        prenom="Anne",
        entreprise="ACME",
        signup_at=datetime(2026, 6, 1, tzinfo=UTC),
        unsubscribe_url="https://app.veridis.fr/unsubscribe/anne",
        properties={"secteur": "industrie"},
    )


@pytest.mark.asyncio
async def test_schedule_onboarding_sequence_creates_seven_trial_emails() -> None:
    repository = FakeEmailQueueRepository()
    scheduler = EmailScheduler(repository)

    scheduled = await scheduler.schedule_onboarding_sequence(user_profile())

    assert len(scheduled) == 7
    assert scheduled[0].template == ScheduledEmailType.WELCOME_TRIAL
    assert scheduled[1].condition == "document_not_uploaded"
    assert scheduled[-1].condition == "trial_not_converted"
    assert repository.queued == scheduled


@pytest.mark.asyncio
async def test_regulatory_digest_respects_marketing_cooldown() -> None:
    repository = FakeEmailQueueRepository(marketing_count=1)
    repository.digest_recipients = [user_profile()]
    scheduler = EmailScheduler(repository)

    queued = await scheduler.send_regulatory_digest()

    assert queued == 0
    assert repository.queued == []


@pytest.mark.asyncio
async def test_regulatory_digest_is_prioritized_when_allowed() -> None:
    repository = FakeEmailQueueRepository(marketing_count=0)
    repository.digest_recipients = [user_profile()]
    scheduler = EmailScheduler(repository)

    queued = await scheduler.send_regulatory_digest()

    assert queued == 1
    assert repository.queued[0].priority == EmailPriority.REGULATORY
    assert repository.queued[0].template == ScheduledEmailType.REGULATORY_ALERT


@pytest.mark.asyncio
async def test_cancel_pending_emails_delegates_reason() -> None:
    repository = FakeEmailQueueRepository()
    scheduler = EmailScheduler(repository)
    user = user_profile()

    cancelled = await scheduler.cancel_pending_emails(user, "document_uploaded")

    assert cancelled == 3
    assert repository.cancelled == [(user.user_id, "document_uploaded")]
