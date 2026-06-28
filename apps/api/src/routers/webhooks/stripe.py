from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

import stripe

from models import Interval, PlanType

StripeEvent = Mapping[str, object]


class StripeWebhookError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class CheckoutActivation:
    event_id: str
    checkout_session_id: str
    stripe_customer_id: str
    stripe_subscription_id: str
    stripe_price_id: str | None
    user_id: str | None
    entreprise_id: UUID | None
    plan: PlanType | None
    interval: Interval | None


@dataclass(frozen=True)
class InvoicePaidUpdate:
    event_id: str
    stripe_customer_id: str
    stripe_subscription_id: str
    invoice_id: str
    next_period_end: datetime | None
    invoice_pdf_url: str | None


@dataclass(frozen=True)
class PaymentFailureUpdate:
    event_id: str
    stripe_customer_id: str
    stripe_subscription_id: str | None
    invoice_id: str
    grace_until: datetime
    attempt_count: int


@dataclass(frozen=True)
class SubscriptionCancellation:
    event_id: str
    stripe_customer_id: str
    stripe_subscription_id: str
    cancelled_at: datetime


class StripeWebhookRepository(Protocol):
    async def has_processed_event(self, event_id: str) -> bool:
        ...

    async def record_event_received(self, event_id: str, event_type: str, payload: str) -> None:
        ...

    async def mark_event_processed(self, event_id: str) -> None:
        ...

    async def mark_event_failed(self, event_id: str, error: str) -> None:
        ...

    async def activate_subscription_from_checkout(self, activation: CheckoutActivation) -> None:
        ...

    async def mark_invoice_paid(self, update: InvoicePaidUpdate) -> None:
        ...

    async def mark_payment_failed(self, update: PaymentFailureUpdate) -> None:
        ...

    async def cancel_subscription(self, cancellation: SubscriptionCancellation) -> None:
        ...


class BillingEmailDispatcher(Protocol):
    async def send_welcome(self, activation: CheckoutActivation) -> None:
        ...

    async def send_invoice_paid(self, update: InvoicePaidUpdate) -> None:
        ...

    async def send_payment_failed(self, update: PaymentFailureUpdate) -> None:
        ...

    async def send_retention(self, cancellation: SubscriptionCancellation) -> None:
        ...


class NullBillingEmailDispatcher:
    async def send_welcome(self, activation: CheckoutActivation) -> None:
        return None

    async def send_invoice_paid(self, update: InvoicePaidUpdate) -> None:
        return None

    async def send_payment_failed(self, update: PaymentFailureUpdate) -> None:
        return None

    async def send_retention(self, cancellation: SubscriptionCancellation) -> None:
        return None


class StripeWebhookHandler:
    """
    Webhook Stripe securise, idempotent et tracable.

    Events traites:
    - checkout.session.completed
    - invoice.paid
    - invoice.payment_failed
    - customer.subscription.deleted
    """

    def __init__(
        self,
        *,
        endpoint_secret: str,
        repository: StripeWebhookRepository,
        email_dispatcher: BillingEmailDispatcher | None = None,
        stripe_module: object = stripe,
        logger: logging.Logger | None = None,
    ) -> None:
        self.endpoint_secret = endpoint_secret
        self.repository = repository
        self.email_dispatcher = email_dispatcher or NullBillingEmailDispatcher()
        self.stripe = stripe_module
        self.logger = logger or logging.getLogger(__name__)

    async def handle(self, payload: bytes, signature: str) -> dict[str, object]:
        event = self._verify_signature(payload, signature)
        event_id = self._required_str(event, "id")
        event_type = self._required_str(event, "type")

        if await self.repository.has_processed_event(event_id):
            self.logger.info("stripe_webhook_duplicate", extra={"event_id": event_id})
            return {"received": True, "duplicate": True, "event_id": event_id}

        await self.repository.record_event_received(
            event_id,
            event_type,
            payload.decode("utf-8", errors="replace"),
        )

        try:
            await self._dispatch(event)
            await self.repository.mark_event_processed(event_id)
            return {"received": True, "duplicate": False, "event_id": event_id}
        except Exception as exc:
            await self.repository.mark_event_failed(event_id, str(exc))
            self.logger.exception("stripe_webhook_failed", extra={"event_id": event_id})
            raise

    def _verify_signature(self, payload: bytes, signature: str) -> StripeEvent:
        try:
            event = self.stripe.Webhook.construct_event(  # type: ignore[attr-defined]
                payload,
                signature,
                self.endpoint_secret,
            )
        except ValueError as exc:
            raise StripeWebhookError(400, "Payload Stripe invalide.") from exc
        except self.stripe.error.SignatureVerificationError as exc:  # type: ignore[attr-defined]
            raise StripeWebhookError(400, "Signature Stripe invalide.") from exc

        return self._event_to_mapping(event)

    async def _dispatch(self, event: StripeEvent) -> None:
        event_type = self._required_str(event, "type")
        if event_type == "checkout.session.completed":
            await self._process_checkout_completed(event)
        elif event_type == "invoice.paid":
            await self._process_invoice_paid(event)
        elif event_type == "invoice.payment_failed":
            await self._process_invoice_payment_failed(event)
        elif event_type == "customer.subscription.deleted":
            await self._process_subscription_cancelled(event)
        else:
            self.logger.info("stripe_webhook_ignored", extra={"event_type": event_type})

    async def _process_checkout_completed(self, event: StripeEvent) -> None:
        session = self._event_object(event)
        metadata = self._mapping_or_empty(session.get("metadata"))
        activation = CheckoutActivation(
            event_id=self._required_str(event, "id"),
            checkout_session_id=self._required_str(session, "id"),
            stripe_customer_id=self._required_str(session, "customer"),
            stripe_subscription_id=self._required_str(session, "subscription"),
            stripe_price_id=self._optional_str(metadata.get("price_id")),
            user_id=self._optional_str(metadata.get("user_id")),
            entreprise_id=self._optional_uuid(metadata.get("entreprise_id")),
            plan=self._optional_plan(metadata.get("plan")),
            interval=self._optional_interval(metadata.get("interval")),
        )
        await self.repository.activate_subscription_from_checkout(activation)
        await self.email_dispatcher.send_welcome(activation)

    async def _process_invoice_paid(self, event: StripeEvent) -> None:
        invoice = self._event_object(event)
        update = InvoicePaidUpdate(
            event_id=self._required_str(event, "id"),
            stripe_customer_id=self._required_str(invoice, "customer"),
            stripe_subscription_id=self._required_str(invoice, "subscription"),
            invoice_id=self._required_str(invoice, "id"),
            next_period_end=self._invoice_period_end(invoice),
            invoice_pdf_url=self._optional_str(invoice.get("invoice_pdf")),
        )
        await self.repository.mark_invoice_paid(update)
        await self.email_dispatcher.send_invoice_paid(update)

    async def _process_invoice_payment_failed(self, event: StripeEvent) -> None:
        invoice = self._event_object(event)
        update = PaymentFailureUpdate(
            event_id=self._required_str(event, "id"),
            stripe_customer_id=self._required_str(invoice, "customer"),
            stripe_subscription_id=self._optional_str(invoice.get("subscription")),
            invoice_id=self._required_str(invoice, "id"),
            grace_until=datetime.now(UTC) + timedelta(days=7),
            attempt_count=self._optional_int(invoice.get("attempt_count")) or 0,
        )
        await self.repository.mark_payment_failed(update)
        await self.email_dispatcher.send_payment_failed(update)

    async def _process_subscription_cancelled(self, event: StripeEvent) -> None:
        subscription = self._event_object(event)
        cancellation = SubscriptionCancellation(
            event_id=self._required_str(event, "id"),
            stripe_customer_id=self._required_str(subscription, "customer"),
            stripe_subscription_id=self._required_str(subscription, "id"),
            cancelled_at=self._timestamp_to_datetime(subscription.get("canceled_at"))
            or datetime.now(UTC),
        )
        await self.repository.cancel_subscription(cancellation)
        await self.email_dispatcher.send_retention(cancellation)

    def _event_object(self, event: StripeEvent) -> Mapping[str, object]:
        data = self._mapping_or_empty(event.get("data"))
        obj = data.get("object")
        if not isinstance(obj, Mapping):
            raise StripeWebhookError(400, "Objet Stripe manquant.")
        return obj

    def _event_to_mapping(self, event: object) -> StripeEvent:
        if isinstance(event, Mapping):
            return event

        to_dict = getattr(event, "to_dict_recursive", None)
        if callable(to_dict):
            value = to_dict()
            if isinstance(value, Mapping):
                return value

        raise StripeWebhookError(400, "Event Stripe non exploitable.")

    def _invoice_period_end(self, invoice: Mapping[str, object]) -> datetime | None:
        lines = self._mapping_or_empty(invoice.get("lines"))
        data = lines.get("data")
        if not isinstance(data, list) or not data:
            return None

        first_line = data[0]
        if not isinstance(first_line, Mapping):
            return None

        period = self._mapping_or_empty(first_line.get("period"))
        return self._timestamp_to_datetime(period.get("end"))

    def _required_str(self, mapping: Mapping[str, object], key: str) -> str:
        value = mapping.get(key)
        if isinstance(value, str) and value:
            return value
        raise StripeWebhookError(400, f"Champ Stripe requis manquant: {key}.")

    def _optional_str(self, value: object) -> str | None:
        return value if isinstance(value, str) and value else None

    def _optional_int(self, value: object) -> int | None:
        if isinstance(value, bool):
            return None
        return value if isinstance(value, int) else None

    def _optional_uuid(self, value: object) -> UUID | None:
        if not isinstance(value, str) or not value:
            return None
        try:
            return UUID(value)
        except ValueError:
            return None

    def _optional_plan(self, value: object) -> PlanType | None:
        if not isinstance(value, str) or not value:
            return None
        try:
            return PlanType(value)
        except ValueError:
            return None

    def _optional_interval(self, value: object) -> Interval | None:
        if not isinstance(value, str) or not value:
            return None
        try:
            return Interval(value)
        except ValueError:
            return None

    def _timestamp_to_datetime(self, value: object) -> datetime | None:
        if isinstance(value, bool) or not isinstance(value, int):
            return None
        return datetime.fromtimestamp(value, tz=UTC)

    def _mapping_or_empty(self, value: object) -> Mapping[str, object]:
        return value if isinstance(value, Mapping) else {}


def parse_stripe_payload(payload: bytes) -> Mapping[str, object]:
    parsed = json.loads(payload.decode("utf-8"))
    if not isinstance(parsed, Mapping):
        raise StripeWebhookError(400, "Payload Stripe JSON invalide.")
    return parsed
