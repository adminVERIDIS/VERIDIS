from __future__ import annotations

from datetime import date

import pytest

from services.analytics.mrr_calculator import MRRCalculator
from services.analytics.schemas import MRRAdjustment, MRRReport, SubscriptionSnapshot


class FakeMRRRepository:
    def __init__(
        self,
        *,
        snapshots: list[SubscriptionSnapshot],
        adjustments: list[MRRAdjustment] | None = None,
        target_cents: int | None = None,
        history: list[MRRReport] | None = None,
    ) -> None:
        self.snapshots = snapshots
        self.adjustments = adjustments or []
        self.target_cents = target_cents
        self.history = history or []

    async def list_subscription_snapshots(self, as_of: date) -> list[SubscriptionSnapshot]:
        return self.snapshots

    async def list_adjustments(self, start_date: date, end_date: date) -> list[MRRAdjustment]:
        return [
            adjustment
            for adjustment in self.adjustments
            if start_date <= adjustment.effective_at <= end_date
        ]

    async def get_mrr_target(self, as_of: date) -> int | None:
        return self.target_cents

    async def list_historical_reports(self, months: int) -> list[MRRReport]:
        return self.history[-months:]


@pytest.mark.asyncio
async def test_calculate_mrr_with_full_composition() -> None:
    as_of = date(2026, 6, 28)
    repository = FakeMRRRepository(
        target_cents=2_000_000,
        adjustments=[
            MRRAdjustment(amount_cents=-5_000, reason="credit commercial", effective_at=date(2026, 6, 8)),
            MRRAdjustment(amount_cents=-99_999, reason="old refund", effective_at=date(2026, 5, 8)),
        ],
        snapshots=[
            SubscriptionSnapshot(
                id="sub_new",
                customer_id="cus_new",
                amount_cents=20_000,
                billing_interval="month",
                status="active",
                started_at=date(2026, 6, 4),
            ),
            SubscriptionSnapshot(
                id="sub_expansion",
                customer_id="cus_expansion",
                amount_cents=35_000,
                billing_interval="month",
                status="active",
                started_at=date(2025, 12, 1),
                previous_mrr_cents=25_000,
            ),
            SubscriptionSnapshot(
                id="sub_contraction",
                customer_id="cus_contraction",
                amount_cents=20_000,
                billing_interval="month",
                status="active",
                started_at=date(2025, 9, 1),
                previous_mrr_cents=30_000,
            ),
            SubscriptionSnapshot(
                id="sub_churn",
                customer_id="cus_churn",
                amount_cents=0,
                billing_interval="month",
                status="cancelled",
                started_at=date(2025, 3, 1),
                previous_mrr_cents=40_000,
                cancelled_at=date(2026, 6, 10),
            ),
            SubscriptionSnapshot(
                id="sub_annual",
                customer_id="cus_annual",
                amount_cents=1_200_000,
                billing_interval="year",
                status="active",
                started_at=date(2025, 1, 1),
                previous_mrr_cents=100_000,
            ),
        ],
    )

    report = await MRRCalculator(repository).calculate(as_of)

    assert report.total_cents == 170_000
    assert report.previous_total_cents == 195_000
    assert report.target_cents == 2_000_000
    assert report.subscriptions_count == 4
    assert report.components.new_cents == 20_000
    assert report.components.expansion_cents == 10_000
    assert report.components.contraction_cents == 10_000
    assert report.components.churn_cents == 40_000
    assert report.components.adjustments_cents == -5_000
    assert report.components.net_growth_cents == -25_000
    assert round(report.growth_rate, 4) == -0.1282


@pytest.mark.asyncio
async def test_reactivation_is_not_double_counted_as_expansion() -> None:
    repository = FakeMRRRepository(
        snapshots=[
            SubscriptionSnapshot(
                id="sub_reactivated",
                customer_id="cus_reactivated",
                amount_cents=49_000,
                billing_interval="month",
                status="active",
                started_at=date(2024, 1, 1),
                previous_mrr_cents=0,
                reactivated_at=date(2026, 6, 12),
            )
        ]
    )

    report = await MRRCalculator(repository).calculate(date(2026, 6, 28))

    assert report.total_cents == 49_000
    assert report.components.reactivation_cents == 49_000
    assert report.components.new_cents == 0
    assert report.components.expansion_cents == 0
