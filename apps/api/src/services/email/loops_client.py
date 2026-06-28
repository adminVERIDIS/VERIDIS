from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx


class AsyncPostDeleteClient(Protocol):
    async def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any],
        timeout: float,
    ) -> Any:
        ...


@dataclass(frozen=True)
class Contact:
    email: str
    id: str | None
    properties: dict[str, Any]


class LoopsClient:
    """Client Loops pour sequences marketing, events et contacts."""

    def __init__(
        self,
        api_key: str,
        *,
        http_client: AsyncPostDeleteClient | None = None,
        base_url: str = "https://app.loops.so/api/v1",
    ) -> None:
        self.api_key = api_key
        self.http_client = http_client or httpx.AsyncClient()
        self.base_url = base_url.rstrip("/")

    async def create_contact(self, email: str, properties: dict[str, Any]) -> Contact:
        payload = {"email": email, **properties}
        data = await self._post("/contacts/create", payload)
        contact_id = data.get("id") if isinstance(data.get("id"), str) else None
        return Contact(email=email, id=contact_id, properties=properties)

    async def trigger_event(
        self,
        email: str,
        event: str,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self._post(
            "/events/send",
            {
                "email": email,
                "eventName": event,
                "properties": properties or {},
            },
        )

    async def add_to_sequence(self, email: str, sequence: str) -> dict[str, Any]:
        return await self.trigger_event(
            email,
            "sequence.entered",
            {"sequence": sequence},
        )

    async def remove_from_sequence(self, email: str, sequence: str) -> dict[str, Any]:
        return await self.trigger_event(
            email,
            "sequence.exited",
            {"sequence": sequence},
        )

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self.http_client.post(
            f"{self.base_url}{path}",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, dict) else {}
