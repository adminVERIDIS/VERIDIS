from __future__ import annotations

import calendar
from collections.abc import Sequence
from datetime import date
from typing import Protocol

from .schemas import (
    MRRAdjustment,
    MRRComponents,
    MRRProjection,
    MRRProjectionPoint,
    MRRReport,
    SubscriptionSnapshot,
)


class MRRDataRepository(Protocol):
    async def list_subscription_snapshots(self, as_of: date) -> Sequence[SubscriptionSnapshot]:
        ...

    async def list_adjustments(self, start_date: date, end_date: date) -> Sequence[MRRAdjustment]:
        ...

    async def get_mrr_target(self, as_of: date) -> int | None:
        ...

    async def list_historical_reports(self, months: int) -> Sequence[MRRReport]:
        ...


class MRRCalculator:
    """
    Calculates precise and traceable Monthly Recurring Revenue.

    Formula:
    MRR = active monthly subscriptions
          + annual subscriptions / 12
          + billing adjustments.

    Composition:
    - New MRR: first paid month for a customer.
    - Expansion MRR: current MRR above previous month.
    - Contraction MRR: current MRR below previous month.
    - Churned MRR: previous MRR lost this month.
    - Reactivation MRR: former customer active again this month.
    """

    revenue_statuses = {"active", "past_due"}
    churn_statuses = {"cancelled", "churned", "read_only"}

    def __init__(self, repository: MRRDataRepository) -> None:
        self.repository = repository

    async def calculate(self, as_of: date) -> MRRReport:
        start_date, end_date = month_bounds(as_of)
        snapshots = list(await self.repository.list_subscription_snapshots(as_of))
        adjustments = list(await self.repository.list_adjustments(start_date, end_date))
        target_cents = await self.repository.get_mrr_target(as_of)

        total_cents = 0
        previous_total_cents = 0
        new_cents = 0
        expansion_cents = 0
        contraction_cents = 0
        churn_cents = 0
        reactivation_cents = 0
        active_count = 0

        for snapshot in snapshots:
            current_mrr_cents = monthly_recurring_cents(snapshot)
            previous_mrr_cents = max(snapshot.previous_mrr_cents, 0)
            previous_total_cents += previous_mrr_cents

            if snapshot.status in self.revenue_statuses:
                total_cents += current_mrr_cents
                active_count += 1

                if is_within_month(snapshot.reactivated_at, start_date, end_date):
                    reactivation_cents += current_mrr_cents
                elif previous_mrr_cents == 0 and is_within_month(snapshot.started_at, start_date, end_date):
                    new_cents += current_mrr_cents
                elif current_mrr_cents > previous_mrr_cents:
                    expansion_cents += current_mrr_cents - previous_mrr_cents
                elif previous_mrr_cents > current_mrr_cents:
                    contraction_cents += previous_mrr_cents - current_mrr_cents

            elif (
                snapshot.status in self.churn_statuses
                and previous_mrr_cents > 0
                and is_within_month(snapshot.cancelled_at, start_date, end_date)
            ):
                churn_cents += previous_mrr_cents

        adjustments_cents = sum(adjustment.amount_cents for adjustment in adjustments)
        total_cents = max(total_cents + adjustments_cents, 0)
        components = MRRComponents(
            new_cents=new_cents,
            expansion_cents=expansion_cents,
            contraction_cents=contraction_cents,
            churn_cents=churn_cents,
            reactivation_cents=reactivation_cents,
            adjustments_cents=adjustments_cents,
        )

        return MRRReport(
            as_of=as_of,
            total_cents=total_cents,
            previous_total_cents=previous_total_cents,
            target_cents=target_cents,
            components=components,
            subscriptions_count=active_count,
        )

    async def project(self, months: int = 12) -> MRRProjection:
        if months <= 0:
            raise ValueError("months must be positive.")

        history = list(await self.repository.list_historical_reports(months=6))
        if not history:
            today = date.today()
            current = await self.calculate(today)
            return MRRProjection(
                start_mrr_cents=current.total_cents,
                months=[
                    MRRProjectionPoint(
                        month=add_months(today.replace(day=1), index + 1),
                        projected_mrr_cents=current.total_cents,
                        confidence=0.5,
                    )
                    for index in range(months)
                ],
                method="flat-no-history",
            )

        latest = history[-1]
        average_growth_cents = round(
            sum(report.components.net_growth_cents for report in history) / len(history)
        )
        projected = latest.total_cents
        points: list[MRRProjectionPoint] = []

        for index in range(months):
            projected = max(projected + average_growth_cents, 0)
            points.append(
                MRRProjectionPoint(
                    month=add_months(latest.as_of.replace(day=1), index + 1),
                    projected_mrr_cents=projected,
                    confidence=max(0.35, 0.85 - index * 0.04),
                )
            )

        return MRRProjection(
            start_mrr_cents=latest.total_cents,
            months=points,
            method="six-month-average-net-mrr-growth",
        )


def monthly_recurring_cents(snapshot: SubscriptionSnapshot) -> int:
    quantity = max(snapshot.quantity, 1)
    amount = max(snapshot.amount_cents, 0) * quantity
    if snapshot.billing_interval == "year":
        return round(amount / 12)
    return amount


def month_bounds(day: date) -> tuple[date, date]:
    last_day = calendar.monthrange(day.year, day.month)[1]
    return day.replace(day=1), day.replace(day=last_day)


def is_within_month(value: date | None, start_date: date, end_date: date) -> bool:
    return value is not None and start_date <= value <= end_date


def add_months(day: date, months: int) -> date:
    month_index = day.month - 1 + months
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last_day))
