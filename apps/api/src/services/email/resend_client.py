from __future__ import annotations

import asyncio
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol

import httpx
from jinja2 import Environment, FileSystemLoader, select_autoescape


class AsyncPostClient(Protocol):
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
class EmailResult:
    provider: str
    message_id: str
    status: str
    template: str
    recipient: str
    attempts: int


@dataclass(frozen=True)
class BaseEmailContext:
    prenom: str
    entreprise: str
    cta_url: str
    unsubscribe_url: str


@dataclass(frozen=True)
class WelcomeContext(BaseEmailContext):
    date_echeance: str
    jours_restant: int
    score_estime: int
    interpretation_score: str
    video_url: str


@dataclass(frozen=True)
class AnalysisContext(BaseEmailContext):
    score: int
    secteur: str
    priorites: list[str]
    dashboard_url: str


@dataclass(frozen=True)
class TrialContext(BaseEmailContext):
    jours_restant: int
    score: int
    gaps_critiques: int
    portal_url: str
    offer_code: str | None = None


@dataclass(frozen=True)
class AlertContext(BaseEmailContext):
    exigence: str
    changement: str
    impact: str
    action: str
    deadline: str


@dataclass(frozen=True)
class ReEngagementContext(BaseEmailContext):
    months_inactive: int
    offer: str
    report_url: str


@dataclass(frozen=True)
class TemplateSpec:
    filename: str
    subject: str
    channel: str = "transactional"
    tags: dict[str, str] = field(default_factory=dict)


TEMPLATE_SPECS = {
    "welcome_trial": TemplateSpec(
        filename="welcome_trial.mjml",
        subject="Bienvenue sur Veridis, votre echeance CSRD en 90 secondes",
        tags={"sequence": "trial", "step": "j0"},
    ),
    "analysis_ready": TemplateSpec(
        filename="analysis_ready.mjml",
        subject="Votre score Veridis est pret",
        tags={"sequence": "trial", "step": "j8"},
    ),
    "trial_expiring": TemplateSpec(
        filename="trial_expiring.mjml",
        subject="J-3 avant la fin de votre essai Veridis",
        tags={"sequence": "trial", "step": "j11"},
    ),
    "regulatory_alert": TemplateSpec(
        filename="regulatory_alert.mjml",
        subject="Nouvelle exigence ESRS applicable a votre entreprise",
        channel="regulatory",
        tags={"sequence": "regulatory"},
    ),
    "re_engagement": TemplateSpec(
        filename="re_engagement.mjml",
        subject="Ce qui a change chez Veridis",
        channel="marketing",
        tags={"sequence": "re_engagement"},
    ),
}


class ResendClient:
    """
    Client Resend transactionnel avec templates MJML rendus par Jinja2.
    """

    def __init__(
        self,
        api_key: str,
        from_email: str,
        from_name: str = "Veridis",
        *,
        template_dir: Path | None = None,
        http_client: AsyncPostClient | None = None,
        max_retries: int = 3,
        retry_base_delay: float = 0.2,
    ) -> None:
        self.api_key = api_key
        self.from_email = from_email
        self.from_name = from_name
        self.http_client = http_client or httpx.AsyncClient()
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self.template_dir = template_dir or Path(__file__).resolve().parent / "templates"
        self.environment = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(enabled_extensions=("mjml", "html")),
            trim_blocks=True,
            lstrip_blocks=True,
            cache_size=64,
        )

    async def send_welcome_trial(self, to: str, context: WelcomeContext) -> EmailResult:
        return await self._send_template("welcome_trial", to, asdict(context))

    async def send_analysis_ready(self, to: str, context: AnalysisContext) -> EmailResult:
        return await self._send_template("analysis_ready", to, asdict(context))

    async def send_trial_expiring(self, to: str, context: TrialContext) -> EmailResult:
        return await self._send_template("trial_expiring", to, asdict(context))

    async def send_regulatory_alert(self, to: str, context: AlertContext) -> EmailResult:
        return await self._send_template("regulatory_alert", to, asdict(context))

    async def send_re_engagement(self, to: str, context: ReEngagementContext) -> EmailResult:
        return await self._send_template("re_engagement", to, asdict(context))

    async def _send_template(
        self,
        template_name: str,
        to: str,
        context: dict[str, Any],
    ) -> EmailResult:
        spec = TEMPLATE_SPECS[template_name]
        rendered_mjml = self.environment.get_template(spec.filename).render(context)
        html = self._mjml_to_html(rendered_mjml)
        payload = self._build_payload(to, spec, html, context)
        response = await self._post_with_retry(payload)
        message_id = self._extract_message_id(response)
        return EmailResult(
            provider="resend",
            message_id=message_id,
            status="sent",
            template=template_name,
            recipient=to,
            attempts=response["attempts"],
        )

    def _build_payload(
        self,
        to: str,
        spec: TemplateSpec,
        html: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "from": f"{self.from_name} <{self.from_email}>",
            "to": [to],
            "subject": spec.subject,
            "html": html,
            "headers": {
                "List-Unsubscribe": f"<{context['unsubscribe_url']}>",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            },
            "tags": [
                {"name": "template", "value": spec.filename.removesuffix(".mjml")},
                *[
                    {"name": name, "value": value}
                    for name, value in spec.tags.items()
                ],
            ],
        }

    async def _post_with_retry(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self.http_client.post(
                    "https://api.resend.com/emails",
                    headers=headers,
                    json=payload,
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict):
                    data = {}
                data["attempts"] = attempt
                return data
            except Exception as exc:
                last_error = exc
                if attempt == self.max_retries:
                    break
                await asyncio.sleep(self.retry_base_delay * attempt)

        raise RuntimeError("Resend email delivery failed") from last_error

    def _extract_message_id(self, response: dict[str, Any]) -> str:
        value = response.get("id") or response.get("message_id")
        return str(value) if value else "unknown"

    def _mjml_to_html(self, rendered_mjml: str) -> str:
        body_match = re.search(r"<mj-body[^>]*>(?P<body>.*)</mj-body>", rendered_mjml, re.DOTALL)
        body = body_match.group("body") if body_match else rendered_mjml
        replacements = {
            "mj-section": "section",
            "mj-column": "div",
            "mj-text": "p",
            "mj-button": "a",
            "mj-image": "img",
            "mj-divider": "hr",
        }
        html = body
        for mjml_tag, html_tag in replacements.items():
            html = re.sub(rf"</{mjml_tag}>", f"</{html_tag}>", html)
            html = re.sub(rf"<{mjml_tag}([^>]*)>", f"<{html_tag}\\1>", html)
        html = re.sub(r"</?mj-[^>]+>", "", html)
        return (
            "<!doctype html><html><body "
            'style="margin:0;background:#fafafa;font-family:Inter,system-ui,sans-serif">'
            f"{html}</body></html>"
        )
