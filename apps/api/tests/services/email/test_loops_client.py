from __future__ import annotations

import pytest

from services.email.loops_client import LoopsClient


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

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
        return FakeResponse({"id": "contact_123", "success": True})


@pytest.mark.asyncio
async def test_create_contact_sends_custom_properties() -> None:
    http_client = FakeHTTPClient()
    client = LoopsClient("loops_test", http_client=http_client)

    contact = await client.create_contact(
        "lea@example.com",
        {"company": "ACME", "score": 52},
    )

    assert contact.id == "contact_123"
    assert http_client.calls[0]["url"].endswith("/contacts/create")
    assert http_client.calls[0]["json"]["company"] == "ACME"


@pytest.mark.asyncio
async def test_sequence_events_are_modeled_as_loops_events() -> None:
    http_client = FakeHTTPClient()
    client = LoopsClient("loops_test", http_client=http_client)

    await client.add_to_sequence("lea@example.com", "trial_14j")
    await client.remove_from_sequence("lea@example.com", "trial_14j")

    assert http_client.calls[0]["json"]["eventName"] == "sequence.entered"
    assert http_client.calls[1]["json"]["eventName"] == "sequence.exited"
    assert http_client.calls[1]["json"]["properties"] == {"sequence": "trial_14j"}
