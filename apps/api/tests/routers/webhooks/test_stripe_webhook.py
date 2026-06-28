from __future__ import annotations

import json
from uuid import uuid4

import pytest

from routers.webhooks.stripe import (
    CheckoutActivation,
    InvoicePaidUpdate,
    PaymentFailureUpdate,
    StripeWebhookError,
    StripeWebhookHandler,
    SubscriptionCancellation,
)


class FakeSignatureVerificationError(Exception):
    """Raised by the fake Stripe SDK when a test signature is invalid."""


class FakeWebhook:
    @staticmethod
    def construct_event(payload: bytes, signature: str, endpoint_secret: str) -> dict[str, object]:
        if endpoint_secret != "endpoint_test_secret" or signature != "valid":
            raise FakeSignatureVerificationError("bad signature")
        value = json.loads(payload.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("payload must be an object")
        return value


class FakeStripeError:
    SignatureVerificationError = FakeSignatureVerificationError


class FakeStripeModule:
    Webhook = FakeWebhook
    error = FakeStripeError


class FakeRepository:
    def __init__(self) -> None:
        self.received: list[str] = []
        self.processed: set[str] = set()
        self.failed: dict[str, str] = {}
        self.activations: list[CheckoutActivation] = []
        self.invoice_paid: list[InvoicePaidUpdate] = []
        self.payment_failed: list[PaymentFailureUpdate] = []
        self.cancellations: list[SubscriptionCancellation] = []

    async def has_processed_event(self, event_id: str) -> bool:
        return event_id in self.processed

    async def record_event_received(self, event_id: str, event_type: str, payload: str) -> None:
        self.received.append(event_id)

    async def mark_event_processed(self, event_id: str) -> None:
        self.processed.add(event_id)

    async def mark_event_failed(self, event_id: str, error: str) -> None:
        self.failed[event_id] = error

    async def activate_subscription_from_checkout(self, activation: CheckoutActivation) -> None:
        self.activations.append(activation)

    async def mark_invoice_paid(self, update: InvoicePaidUpdate) -> None:
        self.invoice_paid.append(update)

    async def mark_payment_failed(self, update: PaymentFailureUpdate) -> None:
        self.payment_failed.append(update)

    async def cancel_subscription(self, cancellation: SubscriptionCancellation) -> None:
        self.cancellations.append(cancellation)


class FakeEmailDispatcher:
    def __init__(self) -> None:
        self.welcome_count = 0
        self.invoice_count = 0
        self.failed_count = 0
        self.retention_count = 0

    async def send_welcome(self, activation: CheckoutActivation) -> None:
        self.welcome_count += 1

    async def send_invoice_paid(self, update: InvoicePaidUpdate) -> None:
        self.invoice_count += 1

    async def send_payment_failed(self, update: PaymentFailureUpdate) -> None:
        self.failed_count += 1

    async def send_retention(self, cancellation: SubscriptionCancellation) -> None:
        self.retention_count += 1


def make_handler(repository: FakeRepository, emails: FakeEmailDispatcher) -> StripeWebhookHandler:
    return StripeWebhookHandler(
        endpoint_secret="endpoint_test_secret",
        repository=repository,
        email_dispatcher=emails,
        stripe_module=FakeStripeModule,
    )


def event_payload(event: dict[str, object]) -> bytes:
    return json.dumps(event).encode("utf-8")


@pytest.mark.asyncio
async def test_checkout_completed_is_processed_once() -> None:
    repository = FakeRepository()
    emails = FakeEmailDispatcher()
    handler = make_handler(repository, emails)
    entreprise_id = uuid4()
    event = {
        "id": "evt_checkout",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test",
                "customer": "cus_test",
                "subscription": "sub_test",
                "metadata": {
                    "user_id": "user_123",
                    "entreprise_id": str(entreprise_id),
                    "plan": "professional",
                    "interval": "year",
                    "price_id": "price_pro_year",
                },
            }
        },
    }

    first = await handler.handle(event_payload(event), "valid")
    second = await handler.handle(event_payload(event), "valid")

    assert first["received"] is True
    assert second["duplicate"] is True
    assert len(repository.activations) == 1
    assert repository.activations[0].entreprise_id == entreprise_id
    assert repository.activations[0].stripe_subscription_id == "sub_test"
    assert emails.welcome_count == 1


@pytest.mark.asyncio
async def test_invoice_paid_updates_next_period_and_invoice_pdf() -> None:
    repository = FakeRepository()
    emails = FakeEmailDispatcher()
    handler = make_handler(repository, emails)
    event = {
        "id": "evt_invoice_paid",
        "type": "invoice.paid",
        "data": {
            "object": {
                "id": "in_test",
                "customer": "cus_test",
                "subscription": "sub_test",
                "invoice_pdf": "https://stripe.test/invoice.pdf",
                "lines": {"data": [{"period": {"end": 1_800_000_000}}]},
            }
        },
    }

    result = await handler.handle(event_payload(event), "valid")

    assert result["received"] is True
    assert repository.invoice_paid[0].invoice_id == "in_test"
    assert repository.invoice_paid[0].next_period_end is not None
    assert emails.invoice_count == 1


@pytest.mark.asyncio
async def test_payment_failed_gets_seven_day_grace_period() -> None:
    repository = FakeRepository()
    emails = FakeEmailDispatcher()
    handler = make_handler(repository, emails)
    event = {
        "id": "evt_payment_failed",
        "type": "invoice.payment_failed",
        "data": {
            "object": {
                "id": "in_failed",
                "customer": "cus_test",
                "subscription": "sub_test",
                "attempt_count": 2,
            }
        },
    }

    await handler.handle(event_payload(event), "valid")

    assert repository.payment_failed[0].attempt_count == 2
    assert repository.payment_failed[0].stripe_subscription_id == "sub_test"
    assert emails.failed_count == 1


@pytest.mark.asyncio
async def test_subscription_deleted_triggers_downgrade_flow() -> None:
    repository = FakeRepository()
    emails = FakeEmailDispatcher()
    handler = make_handler(repository, emails)
    event = {
        "id": "evt_deleted",
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_test",
                "customer": "cus_test",
                "canceled_at": 1_800_000_001,
            }
        },
    }

    await handler.handle(event_payload(event), "valid")

    assert repository.cancellations[0].stripe_subscription_id == "sub_test"
    assert emails.retention_count == 1


@pytest.mark.asyncio
async def test_invalid_signature_raises_400() -> None:
    repository = FakeRepository()
    emails = FakeEmailDispatcher()
    handler = make_handler(repository, emails)
    event = {"id": "evt_bad", "type": "invoice.paid", "data": {"object": {}}}

    with pytest.raises(StripeWebhookError) as exc:
        await handler.handle(event_payload(event), "invalid")

    assert exc.value.status_code == 400
    assert repository.received == []
