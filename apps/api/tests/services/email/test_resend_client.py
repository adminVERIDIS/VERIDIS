from __future__ import annotations

import pytest

from services.email import ResendClient, TrialContext, WelcomeContext


class FakeResponse:
    def __init__(self, payload: dict[str, object], status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> dict[str, object]:
        return self.payload


class FakeHTTPClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, object],
        timeout: float,
    ) -> FakeResponse:
        self.calls.append(
            {
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": timeout,
            }
        )
        return FakeResponse({"id": "email_test_123"})


@pytest.mark.asyncio
async def test_send_welcome_trial_renders_personalized_email() -> None:
    http_client = FakeHTTPClient()
    client = ResendClient(
        api_key="resend_test",
        from_email="founder@veridis.fr",
        http_client=http_client,
        retry_base_delay=0,
    )
    context = WelcomeContext(
        prenom="Sarah",
        entreprise="ACME",
        date_echeance="31/12/2026",
        jours_restant=90,
        score_estime=47,
        interpretation_score="Conformite partielle",
        cta_url="https://app.veridis.fr/upload",
        video_url="https://loom.test/demo",
        unsubscribe_url="https://app.veridis.fr/unsubscribe/u_123",
    )

    result = await client.send_welcome_trial("sarah@example.com", context)

    assert result.message_id == "email_test_123"
    payload = http_client.calls[0]["json"]
    assert payload["to"] == ["sarah@example.com"]
    assert "Sarah" in payload["html"]
    assert "ACME" in payload["html"]
    assert payload["headers"]["List-Unsubscribe"] == "<https://app.veridis.fr/unsubscribe/u_123>"
    assert payload["headers"]["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"


@pytest.mark.asyncio
async def test_send_trial_expiring_includes_offer_and_portal_cta() -> None:
    http_client = FakeHTTPClient()
    client = ResendClient(
        api_key="resend_test",
        from_email="founder@veridis.fr",
        http_client=http_client,
        retry_base_delay=0,
    )
    context = TrialContext(
        prenom="Marc",
        entreprise="RSE Conseil",
        cta_url="https://app.veridis.fr",
        unsubscribe_url="https://app.veridis.fr/unsubscribe/u_456",
        jours_restant=3,
        score=61,
        gaps_critiques=4,
        portal_url="https://billing.stripe.test/session",
        offer_code="EARLY30",
    )

    result = await client.send_trial_expiring("marc@example.com", context)

    payload = http_client.calls[0]["json"]
    assert result.template == "trial_expiring"
    assert "EARLY30" in payload["html"]
    assert "https://billing.stripe.test/session" in payload["html"]
    assert payload["tags"][1] == {"name": "sequence", "value": "trial"}
