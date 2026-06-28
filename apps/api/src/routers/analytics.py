from __future__ import annotations

from datetime import date
from typing import Literal, Protocol

from services.analytics.alert_engine import Alert, AlertEngine
from services.analytics.mrr_calculator import MRRCalculator
from services.analytics.schemas import (
    FunnelAnalytics,
    MRRSeriesPoint,
    MRRTimeSeries,
    PaginatedResponse,
)

Granularity = Literal["day", "week", "month"]
CustomerStatus = Literal["trial_active", "active", "past_due", "cancelled", "churned"]
PlanType = Literal["essential", "professional", "enterprise"]
SortOrder = Literal["asc", "desc"]

ALLOWED_CUSTOMER_SORTS = {
    "mrr",
    "entreprise",
    "score",
    "status",
    "last_activity",
    "next_deadline",
}


class AnalyticsCache(Protocol):
    async def get(self, key: str) -> object | None:
        ...

    async def set(self, key: str, value: object, ttl_seconds: int) -> None:
        ...


class NullAnalyticsCache:
    async def get(self, key: str) -> object | None:
        return None

    async def set(self, key: str, value: object, ttl_seconds: int) -> None:
        return None


class AnalyticsRepository(Protocol):
    async def get_mrr_time_series(
        self,
        start_date: date,
        end_date: date,
        granularity: Granularity,
    ) -> MRRTimeSeries | None:
        ...

    async def get_funnel(self, start_date: date, end_date: date) -> FunnelAnalytics:
        ...

    async def list_customers(
        self,
        *,
        status: CustomerStatus | None,
        plan: PlanType | None,
        search: str | None,
        sort_by: str,
        sort_order: SortOrder,
        page: int,
        page_size: int,
    ) -> PaginatedResponse:
        ...


class AnalyticsRouter:
    """
    Founder analytics API.

    Performance notes:
    - MRR is cached for 5 minutes and can be recomputed hourly by a worker.
    - Funnel data should come from a materialized view refreshed every 4 hours.
    - Customer table is paginated, filterable and index-friendly.
    - Every endpoint is admin-only at the HTTP layer that mounts this router.
    """

    MRR_TTL_SECONDS = 300
    FUNNEL_TTL_SECONDS = 300
    CUSTOMERS_TTL_SECONDS = 120
    ALERTS_TTL_SECONDS = 60

    def __init__(
        self,
        *,
        mrr_calculator: MRRCalculator,
        repository: AnalyticsRepository,
        alert_engine: AlertEngine,
        cache: AnalyticsCache | None = None,
    ) -> None:
        self.mrr_calculator = mrr_calculator
        self.repository = repository
        self.alert_engine = alert_engine
        self.cache = cache or NullAnalyticsCache()

    async def get_mrr(
        self,
        start_date: date,
        end_date: date,
        granularity: Granularity = "month",
    ) -> MRRTimeSeries:
        cache_key = f"analytics:mrr:{start_date.isoformat()}:{end_date.isoformat()}:{granularity}"
        cached = await self.cache.get(cache_key)
        if isinstance(cached, MRRTimeSeries):
            return cached

        series = await self.repository.get_mrr_time_series(start_date, end_date, granularity)
        if series is None:
            report = await self.mrr_calculator.calculate(end_date)
            series = MRRTimeSeries(
                start_date=start_date,
                end_date=end_date,
                granularity=granularity,
                points=[MRRSeriesPoint(period_start=end_date.replace(day=1), report=report)],
            )

        await self.cache.set(cache_key, series, ttl_seconds=self.MRR_TTL_SECONDS)
        return series

    async def get_funnel(self, start_date: date, end_date: date) -> FunnelAnalytics:
        cache_key = f"analytics:funnel:{start_date.isoformat()}:{end_date.isoformat()}"
        cached = await self.cache.get(cache_key)
        if isinstance(cached, FunnelAnalytics):
            return cached

        funnel = await self.repository.get_funnel(start_date, end_date)
        await self.cache.set(cache_key, funnel, ttl_seconds=self.FUNNEL_TTL_SECONDS)
        return funnel

    async def list_customers(
        self,
        status: CustomerStatus | None = None,
        plan: PlanType | None = None,
        search: str | None = None,
        sort_by: str = "mrr",
        sort_order: SortOrder = "desc",
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedResponse:
        if sort_by not in ALLOWED_CUSTOMER_SORTS:
            raise ValueError(f"Unsupported analytics customer sort: {sort_by}.")
        if page < 1:
            raise ValueError("page must be >= 1.")
        if page_size < 1 or page_size > 100:
            raise ValueError("page_size must be between 1 and 100.")

        cache_key = (
            "analytics:customers:"
            f"{status or 'all'}:{plan or 'all'}:{search or ''}:{sort_by}:{sort_order}:{page}:{page_size}"
        )
        cached = await self.cache.get(cache_key)
        if isinstance(cached, PaginatedResponse):
            return cached

        customers = await self.repository.list_customers(
            status=status,
            plan=plan,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
        await self.cache.set(cache_key, customers, ttl_seconds=self.CUSTOMERS_TTL_SECONDS)
        return customers

    async def get_active_alerts(self) -> list[Alert]:
        cached = await self.cache.get("analytics:alerts:active")
        if isinstance(cached, list) and all(isinstance(alert, Alert) for alert in cached):
            return cached

        alerts = await self.alert_engine.evaluate_all()
        await self.cache.set("analytics:alerts:active", alerts, ttl_seconds=self.ALERTS_TTL_SECONDS)
        return alerts

    async def get_dashboard(self, start_date: date, end_date: date) -> dict[str, object]:
        """
        Aggregated endpoint for the web dashboard polling path.

        The web UI can call the specific endpoints independently, but this single
        payload keeps mobile startup fast when the founder opens the dashboard.
        """

        mrr = await self.get_mrr(start_date, end_date, granularity="month")
        funnel = await self.get_funnel(start_date, end_date)
        customers = await self.list_customers(page=1, page_size=50)
        alerts = await self.get_active_alerts()
        return {
            "mrr": mrr,
            "funnel": funnel,
            "customers": customers,
            "alerts": alerts,
        }
