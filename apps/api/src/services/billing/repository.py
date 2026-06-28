from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    Abonnement,
    Interval,
    PlanType,
    RapportCSRD,
    StripeWebhookEvent,
    SubscriptionStatus,
    WebhookEventStatus,
)
from routers.webhooks.stripe import (
    CheckoutActivation,
    InvoicePaidUpdate,
    PaymentFailureUpdate,
    SubscriptionCancellation,
)


class SQLAlchemyBillingRepository:
    """Repository async pour webhooks Stripe et entitlements billing."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def has_processed_event(self, event_id: str) -> bool:
        event = await self.session.get(StripeWebhookEvent, event_id)
        return event is not None and event.status == WebhookEventStatus.PROCESSED

    async def record_event_received(self, event_id: str, event_type: str, payload: str) -> None:
        event = await self.session.get(StripeWebhookEvent, event_id)
        if event is None:
            self.session.add(
                StripeWebhookEvent(
                    event_id=event_id,
                    event_type=event_type,
                    status=WebhookEventStatus.RECEIVED,
                    payload=payload,
                )
            )
        elif event.status != WebhookEventStatus.PROCESSED:
            event.status = WebhookEventStatus.RECEIVED
            event.payload = payload
            event.error = None
        await self.session.flush()

    async def mark_event_processed(self, event_id: str) -> None:
        event = await self.session.get(StripeWebhookEvent, event_id)
        if event is not None:
            event.status = WebhookEventStatus.PROCESSED
            event.error = None
        await self.session.flush()

    async def mark_event_failed(self, event_id: str, error: str) -> None:
        event = await self.session.get(StripeWebhookEvent, event_id)
        if event is not None:
            event.status = WebhookEventStatus.FAILED
            event.error = error[:2000]
        await self.session.flush()

    async def activate_subscription_from_checkout(self, activation: CheckoutActivation) -> None:
        if activation.entreprise_id is None:
            raise ValueError("checkout.session.completed requires entreprise_id metadata.")

        now = datetime.now(UTC)
        interval = activation.interval or Interval.YEAR
        plan = activation.plan or PlanType.ESSENTIAL
        abonnement = await self._subscription_by_stripe_id(activation.stripe_subscription_id)
        limits = self._limits_for_plan(plan)
        period_end = now + (timedelta(days=365) if interval == Interval.YEAR else timedelta(days=30))

        if abonnement is None:
            abonnement = Abonnement(
                entreprise_id=activation.entreprise_id,
                stripe_customer_id=activation.stripe_customer_id,
                stripe_subscription_id=activation.stripe_subscription_id,
                stripe_price_id=activation.stripe_price_id or "",
                plan=plan,
                status=SubscriptionStatus.TRIAL_ACTIVE,
                billing_interval=interval,
                trial_start=now,
                trial_end=now + timedelta(days=14),
                current_period_start=now,
                current_period_end=period_end,
                cancel_at_period_end=False,
                cancelled_at=None,
                max_rapports=limits["max_rapports"],
                max_utilisateurs=limits["max_utilisateurs"],
                features=limits["features"],
            )
            self.session.add(abonnement)
        else:
            abonnement.stripe_customer_id = activation.stripe_customer_id
            abonnement.stripe_price_id = activation.stripe_price_id or abonnement.stripe_price_id
            abonnement.plan = plan
            abonnement.status = SubscriptionStatus.TRIAL_ACTIVE
            abonnement.billing_interval = interval
            abonnement.trial_end = now + timedelta(days=14)
            abonnement.current_period_end = period_end
            abonnement.max_rapports = limits["max_rapports"]
            abonnement.max_utilisateurs = limits["max_utilisateurs"]
            abonnement.features = limits["features"]

        await self.session.flush()

    async def mark_invoice_paid(self, update: InvoicePaidUpdate) -> None:
        abonnement = await self._subscription_by_stripe_id(update.stripe_subscription_id)
        if abonnement is not None:
            abonnement.status = SubscriptionStatus.ACTIVE
            if update.next_period_end is not None:
                abonnement.current_period_end = update.next_period_end
        await self.session.flush()

    async def mark_payment_failed(self, update: PaymentFailureUpdate) -> None:
        if update.stripe_subscription_id is None:
            return
        abonnement = await self._subscription_by_stripe_id(update.stripe_subscription_id)
        if abonnement is not None:
            abonnement.status = SubscriptionStatus.PAST_DUE
            abonnement.current_period_end = max(abonnement.current_period_end, update.grace_until)
        await self.session.flush()

    async def cancel_subscription(self, cancellation: SubscriptionCancellation) -> None:
        abonnement = await self._subscription_by_stripe_id(cancellation.stripe_subscription_id)
        if abonnement is not None:
            abonnement.status = SubscriptionStatus.READ_ONLY
            abonnement.cancelled_at = cancellation.cancelled_at
            abonnement.cancel_at_period_end = False
        await self.session.flush()

    async def get_current_abonnement(self, entreprise_id: UUID) -> Abonnement | None:
        result = await self.session.execute(
            select(Abonnement)
            .where(Abonnement.entreprise_id == entreprise_id)
            .order_by(Abonnement.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def count_rapports_for_period(
        self,
        entreprise_id: UUID,
        abonnement: Abonnement,
    ) -> int:
        statement: Select[tuple[int]] = select(func.count(RapportCSRD.id)).where(
            RapportCSRD.entreprise_id == entreprise_id,
            RapportCSRD.created_at >= abonnement.current_period_start,
            RapportCSRD.created_at <= abonnement.current_period_end,
        )
        result = await self.session.execute(statement)
        return int(result.scalar_one())

    async def count_users(self, entreprise_id: UUID) -> int:
        return 1

    async def _subscription_by_stripe_id(self, subscription_id: str) -> Abonnement | None:
        result = await self.session.execute(
            select(Abonnement).where(Abonnement.stripe_subscription_id == subscription_id).limit(1)
        )
        return result.scalar_one_or_none()

    def _limits_for_plan(self, plan: PlanType) -> dict[str, object]:
        if plan == PlanType.ENTERPRISE:
            return {
                "max_rapports": None,
                "max_utilisateurs": 10,
                "features": {
                    "api_access": True,
                    "benchmark": True,
                    "white_label_pdf": True,
                    "sla_4h": True,
                    "onboarding_call": True,
                },
            }
        if plan == PlanType.PROFESSIONAL:
            return {
                "max_rapports": 3,
                "max_utilisateurs": 3,
                "features": {
                    "api_access": False,
                    "benchmark": True,
                    "white_label_pdf": False,
                    "realtime_chat": True,
                },
            }
        return {
            "max_rapports": 1,
            "max_utilisateurs": 1,
            "features": {
                "api_access": False,
                "benchmark": False,
                "white_label_pdf": False,
                "email_support": True,
            },
        }
