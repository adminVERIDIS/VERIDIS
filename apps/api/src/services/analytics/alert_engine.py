from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import ClassVar, Literal, Protocol

from .schemas import MetricSeverity, MetricSnapshot

AlertCondition = Literal["gt", "lt", "lt_target", "gt_target"]
AlertChannel = Literal["email", "slack", "in_app"]


@dataclass(frozen=True)
class AlertRule:
    id: str
    metric: str
    condition: AlertCondition
    severity: MetricSeverity
    message: str
    action: str
    threshold: float | None = None
    channels: tuple[AlertChannel, ...] = ("slack", "in_app")


@dataclass(frozen=True)
class Alert:
    id: str
    rule_id: str
    metric: str
    value: float
    threshold: float
    severity: MetricSeverity
    message: str
    action: str
    channels: tuple[AlertChannel, ...]
    triggered_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class MetricRepository(Protocol):
    async def get_latest_metrics(self) -> dict[str, MetricSnapshot]:
        ...


class AlertRepository(Protocol):
    async def replace_active_alerts(self, alerts: list[Alert]) -> None:
        ...


class AlertNotifier(Protocol):
    async def send_email(self, alert: Alert) -> None:
        ...

    async def send_slack(self, alert: Alert) -> None:
        ...


class NullAlertRepository:
    async def replace_active_alerts(self, alerts: list[Alert]) -> None:
        return None


class NullAlertNotifier:
    async def send_email(self, alert: Alert) -> None:
        return None

    async def send_slack(self, alert: Alert) -> None:
        return None


class AlertEngine:
    """
    Evaluates founder analytics rules and notifies critical deviations.

    Schedule: run every hour from a worker or cron.
    Channels: email for critical alerts, Slack for every active rule, in-app via repository.
    """

    RULES: ClassVar[list[AlertRule]] = [
        AlertRule(
            id="mrr-behind",
            metric="mrr",
            condition="lt_target",
            severity="critical",
            message="MRR mensuel sous objectif de {gap} EUR.",
            action="Review funnel acquisition + outreach prospects chauds",
            channels=("email", "slack", "in_app"),
        ),
        AlertRule(
            id="new-trials-low",
            metric="new_trials_7d",
            condition="lt",
            threshold=5,
            severity="warning",
            message="Nouveaux trials sous 5/semaine.",
            action="Relancer campagnes acquisition et verifier tracking landing",
        ),
        AlertRule(
            id="trial-conversion-low",
            metric="trial_to_paid",
            condition="lt",
            threshold=15,
            severity="critical",
            message="Trial-to-paid sous 15%.",
            action="Auditer onboarding, email J+2 et friction carte Stripe",
            channels=("email", "slack", "in_app"),
        ),
        AlertRule(
            id="churn-high",
            metric="churn_monthly",
            condition="gt",
            threshold=8,
            severity="critical",
            message="Churn mensuel au-dessus de 8%.",
            action="Lancer interviews churn et sequence retention",
            channels=("email", "slack", "in_app"),
        ),
        AlertRule(
            id="cac-high",
            metric="cac_cents",
            condition="gt",
            threshold=80_000,
            severity="warning",
            message="CAC au-dessus de 800 EUR.",
            action="Couper canaux non rentables et prioriser referrals",
        ),
        AlertRule(
            id="ltv-low",
            metric="ltv_cents",
            condition="lt",
            threshold=500_000,
            severity="warning",
            message="LTV sous 5 000 EUR.",
            action="Revoir packaging annuel et expansion Pro",
        ),
        AlertRule(
            id="ltv-cac-low",
            metric="ltv_cac_ratio",
            condition="lt",
            threshold=2,
            severity="critical",
            message="Ratio LTV/CAC sous 2x.",
            action="Stopper acquisition payante tant que conversion et churn ne sont pas corriges",
            channels=("email", "slack", "in_app"),
        ),
        AlertRule(
            id="activation-low",
            metric="activation_rate",
            condition="lt",
            threshold=60,
            severity="warning",
            message="Activation sous 60%.",
            action="Simplifier upload document et checklist premier score",
        ),
        AlertRule(
            id="time-to-value-high",
            metric="time_to_value_seconds",
            condition="gt",
            threshold=300,
            severity="warning",
            message="Time-to-value au-dessus de 5 minutes.",
            action="Reduire etapes wizard et accelerer analyse initiale",
        ),
        AlertRule(
            id="feature-usage-low",
            metric="feature_usage_rate",
            condition="lt",
            threshold=80,
            severity="warning",
            message="Usage analyse mensuel sous 80%.",
            action="Envoyer alertes reactivation aux comptes dormants",
        ),
        AlertRule(
            id="nps-low",
            metric="nps",
            condition="lt",
            threshold=40,
            severity="warning",
            message="NPS sous 40.",
            action="Planifier interviews detracteurs",
        ),
        AlertRule(
            id="support-high",
            metric="support_tickets_per_100",
            condition="gt",
            threshold=5,
            severity="warning",
            message="Support tickets au-dessus de 5 / 100 clients / mois.",
            action="Prioriser documentation et correction UX recurrente",
        ),
        AlertRule(
            id="uptime-low",
            metric="uptime_api",
            condition="lt",
            threshold=99.9,
            severity="critical",
            message="Uptime API sous 99.9%.",
            action="Ouvrir incident et verifier provider/runtime",
            channels=("email", "slack", "in_app"),
        ),
        AlertRule(
            id="analysis-time-high",
            metric="average_analysis_seconds",
            condition="gt",
            threshold=120,
            severity="warning",
            message="Temps analyse moyen au-dessus de 2 minutes.",
            action="Profiler parsing, queue et appels LLM",
        ),
        AlertRule(
            id="api-500-high",
            metric="errors_500_day",
            condition="gt",
            threshold=5,
            severity="critical",
            message="Erreurs 500 au-dessus de 5/jour.",
            action="Analyser logs et rollback si regression recente",
            channels=("email", "slack", "in_app"),
        ),
        AlertRule(
            id="api-p95-high",
            metric="api_p95_ms",
            condition="gt",
            threshold=500,
            severity="warning",
            message="Temps reponse API p95 au-dessus de 500ms.",
            action="Verifier requetes dashboard, indexes et cache Redis",
        ),
    ]

    def __init__(
        self,
        metric_repository: MetricRepository,
        *,
        alert_repository: AlertRepository | None = None,
        notifier: AlertNotifier | None = None,
        rules: list[AlertRule] | None = None,
    ) -> None:
        self.metric_repository = metric_repository
        self.alert_repository = alert_repository or NullAlertRepository()
        self.notifier = notifier or NullAlertNotifier()
        self.rules = rules or self.RULES

    async def evaluate_all(self) -> list[Alert]:
        metrics = await self.metric_repository.get_latest_metrics()
        alerts = [
            alert
            for rule in self.rules
            if (alert := self._evaluate_rule(rule, metrics.get(rule.metric))) is not None
        ]

        await self.alert_repository.replace_active_alerts(alerts)
        for alert in alerts:
            if "slack" in alert.channels:
                await self.notifier.send_slack(alert)
            if alert.severity == "critical" and "email" in alert.channels:
                await self.notifier.send_email(alert)

        return alerts

    def _evaluate_rule(self, rule: AlertRule, snapshot: MetricSnapshot | None) -> Alert | None:
        if snapshot is None:
            return None

        threshold = self._threshold_for(rule, snapshot)
        if threshold is None or not self._is_triggered(rule.condition, snapshot.value, threshold):
            return None

        gap = abs(threshold - snapshot.value)
        message = rule.message.format(
            value=round(snapshot.value, 2),
            threshold=round(threshold, 2),
            gap=round(gap, 2),
            unit=snapshot.unit,
        )

        return Alert(
            id=f"{rule.id}:{snapshot.observed_at.isoformat()}",
            rule_id=rule.id,
            metric=rule.metric,
            value=snapshot.value,
            threshold=threshold,
            severity=rule.severity,
            message=message,
            action=rule.action,
            channels=rule.channels,
            triggered_at=snapshot.observed_at,
        )

    def _threshold_for(self, rule: AlertRule, snapshot: MetricSnapshot) -> float | None:
        if rule.condition in {"lt_target", "gt_target"}:
            return snapshot.target
        return rule.threshold

    def _is_triggered(self, condition: AlertCondition, value: float, threshold: float) -> bool:
        if condition in {"gt", "gt_target"}:
            return value > threshold
        return value < threshold
