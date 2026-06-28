from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Literal

MetricSeverity = Literal["info", "warning", "critical"]
BillingInterval = Literal["month", "year"]
SubscriptionRevenueStatus = Literal[
    "trial_active",
    "active",
    "past_due",
    "cancelled",
    "churned",
    "read_only",
]


@dataclass(frozen=True)
class SubscriptionSnapshot:
    id: str
    customer_id: str
    amount_cents: int
    billing_interval: BillingInterval
    status: SubscriptionRevenueStatus
    started_at: date
    quantity: int = 1
    previous_mrr_cents: int = 0
    cancelled_at: date | None = None
    reactivated_at: date | None = None


@dataclass(frozen=True)
class MRRAdjustment:
    amount_cents: int
    reason: str
    effective_at: date


@dataclass(frozen=True)
class MRRComponents:
    new_cents: int = 0
    expansion_cents: int = 0
    contraction_cents: int = 0
    churn_cents: int = 0
    reactivation_cents: int = 0
    adjustments_cents: int = 0

    @property
    def net_growth_cents(self) -> int:
        return (
            self.new_cents
            + self.expansion_cents
            - self.contraction_cents
            - self.churn_cents
            + self.reactivation_cents
            + self.adjustments_cents
        )


@dataclass(frozen=True)
class MRRReport:
    as_of: date
    total_cents: int
    previous_total_cents: int
    target_cents: int | None
    components: MRRComponents
    subscriptions_count: int
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def growth_rate(self) -> float:
        if self.previous_total_cents <= 0:
            return 0.0
        return self.components.net_growth_cents / self.previous_total_cents


@dataclass(frozen=True)
class MRRProjectionPoint:
    month: date
    projected_mrr_cents: int
    confidence: float


@dataclass(frozen=True)
class MRRProjection:
    start_mrr_cents: int
    months: list[MRRProjectionPoint]
    method: str


@dataclass(frozen=True)
class MRRSeriesPoint:
    period_start: date
    report: MRRReport


@dataclass(frozen=True)
class MRRTimeSeries:
    start_date: date
    end_date: date
    granularity: Literal["day", "week", "month"]
    points: list[MRRSeriesPoint]


@dataclass(frozen=True)
class FunnelStepAnalytics:
    name: str
    count: int
    conversion_rate: float
    global_conversion_rate: float
    drop_off_reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FunnelAnalytics:
    start_date: date
    end_date: date
    steps: list[FunnelStepAnalytics]
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class CustomerAnalytics:
    id: str
    entreprise_name: str
    siren: str
    plan: Literal["essential", "professional", "enterprise"]
    mrr_cents: int
    average_conformity_score: float | None
    status: Literal["trial_active", "active", "past_due", "cancelled", "churned"]
    last_activity_at: datetime
    next_csrd_deadline: date
    health_score: Literal["green", "yellow", "red"]


@dataclass(frozen=True)
class PaginatedResponse:
    items: list[CustomerAnalytics]
    page: int
    page_size: int
    total: int


@dataclass(frozen=True)
class MetricSnapshot:
    metric: str
    value: float
    target: float | None = None
    unit: str = ""
    observed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
