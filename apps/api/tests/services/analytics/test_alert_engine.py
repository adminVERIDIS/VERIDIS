from __future__ import annotations

from datetime import UTC, datetime

import pytest

from services.analytics.alert_engine import Alert, AlertEngine
from services.analytics.schemas import MetricSnapshot


class FakeMetricRepository:
    def __init__(self, metrics: dict[str, MetricSnapshot]) -> None:
        self.metrics = metrics

    async def get_latest_metrics(self) -> dict[str, MetricSnapshot]:
        return self.metrics


class FakeAlertRepository:
    def __init__(self) -> None:
        self.saved: list[Alert] = []

    async def replace_active_alerts(self, alerts: list[Alert]) -> None:
        self.saved = alerts


class SpyNotifier:
    def __init__(self) -> None:
        self.email_alerts: list[Alert] = []
        self.slack_alerts: list[Alert] = []

    async def send_email(self, alert: Alert) -> None:
        self.email_alerts.append(alert)

    async def send_slack(self, alert: Alert) -> None:
        self.slack_alerts.append(alert)


@pytest.mark.asyncio
async def test_alert_engine_triggers_expected_rules_and_channels() -> None:
    observed_at = datetime(2026, 6, 28, 8, 0, tzinfo=UTC)
    alert_repository = FakeAlertRepository()
    notifier = SpyNotifier()
    engine = AlertEngine(
        FakeMetricRepository(
            {
                "mrr": MetricSnapshot(
                    metric="mrr",
                    value=1_245_000,
                    target=2_000_000,
                    unit="cents",
                    observed_at=observed_at,
                ),
                "trial_to_paid": MetricSnapshot(
                    metric="trial_to_paid",
                    value=12.5,
                    unit="percent",
                    observed_at=observed_at,
                ),
                "churn_monthly": MetricSnapshot(
                    metric="churn_monthly",
                    value=4.2,
                    unit="percent",
                    observed_at=observed_at,
                ),
                "api_p95_ms": MetricSnapshot(
                    metric="api_p95_ms",
                    value=640,
                    unit="ms",
                    observed_at=observed_at,
                ),
            }
        ),
        alert_repository=alert_repository,
        notifier=notifier,
    )

    alerts = await engine.evaluate_all()

    rule_ids = {alert.rule_id for alert in alerts}
    assert rule_ids == {"mrr-behind", "trial-conversion-low", "api-p95-high"}
    assert alert_repository.saved == alerts
    assert {alert.rule_id for alert in notifier.slack_alerts} == rule_ids
    assert {alert.rule_id for alert in notifier.email_alerts} == {
        "mrr-behind",
        "trial-conversion-low",
    }


@pytest.mark.asyncio
async def test_alert_engine_does_not_alert_inside_thresholds() -> None:
    engine = AlertEngine(
        FakeMetricRepository(
            {
                "mrr": MetricSnapshot(metric="mrr", value=2_200_000, target=2_000_000),
                "new_trials_7d": MetricSnapshot(metric="new_trials_7d", value=11),
                "activation_rate": MetricSnapshot(metric="activation_rate", value=68),
                "uptime_api": MetricSnapshot(metric="uptime_api", value=99.96),
            }
        )
    )

    assert await engine.evaluate_all() == []
