from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from models import Abonnement, Interval, PlanType, SubscriptionStatus
from services.billing.entitlements import EntitlementService, FeatureFlag


class FakeBillingRepository:
    def __init__(
        self,
        abonnement: Abonnement | None,
        *,
        rapports_count: int = 0,
        users_count: int = 0,
    ) -> None:
        self.abonnement = abonnement
        self.rapports_count = rapports_count
        self.users_count = users_count

    def get_current_abonnement(self, entreprise_id: UUID) -> Abonnement | None:
        return self.abonnement

    def count_rapports_for_period(self, entreprise_id: UUID, abonnement: Abonnement) -> int:
        return self.rapports_count

    def count_users(self, entreprise_id: UUID) -> int:
        return self.users_count


def build_subscription(
    *,
    plan: PlanType = PlanType.PROFESSIONAL,
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE,
    max_rapports: int | None = 3,
    max_utilisateurs: int = 3,
    features: dict[str, bool] | None = None,
) -> Abonnement:
    now = datetime.now(UTC)
    return Abonnement(
        entreprise_id=uuid4(),
        stripe_customer_id="cus_test",
        stripe_subscription_id="sub_test",
        stripe_price_id="price_test",
        plan=plan,
        status=status,
        billing_interval=Interval.YEAR,
        trial_start=now,
        trial_end=now + timedelta(days=14),
        current_period_start=now,
        current_period_end=now + timedelta(days=365),
        cancel_at_period_end=False,
        cancelled_at=None,
        max_rapports=max_rapports,
        max_utilisateurs=max_utilisateurs,
        features=features or {},
    )


def test_can_create_report_until_plan_quota_is_reached() -> None:
    abonnement = build_subscription(max_rapports=3)
    service = EntitlementService(FakeBillingRepository(abonnement, rapports_count=2))

    assert service.can_create_rapport(abonnement.entreprise_id) is True

    blocked = EntitlementService(FakeBillingRepository(abonnement, rapports_count=3))
    assert blocked.can_create_rapport(abonnement.entreprise_id) is False


def test_enterprise_has_unlimited_reports_and_api_access() -> None:
    abonnement = build_subscription(
        plan=PlanType.ENTERPRISE,
        max_rapports=None,
        max_utilisateurs=10,
    )
    service = EntitlementService(FakeBillingRepository(abonnement, rapports_count=200))

    assert service.can_create_rapport(abonnement.entreprise_id) is True
    assert service.has_feature(abonnement.entreprise_id, FeatureFlag.API_ACCESS) is True


def test_cached_feature_flag_can_disable_plan_feature() -> None:
    abonnement = build_subscription(features={FeatureFlag.BENCHMARK.value: False})
    service = EntitlementService(FakeBillingRepository(abonnement))

    assert service.has_feature(abonnement.entreprise_id, FeatureFlag.BENCHMARK) is False


def test_no_active_subscription_blocks_premium_actions() -> None:
    abonnement = build_subscription(status=SubscriptionStatus.CANCELLED)
    service = EntitlementService(FakeBillingRepository(abonnement))

    assert service.can_create_rapport(abonnement.entreprise_id) is False
    assert service.can_add_user(abonnement.entreprise_id) is False
    assert service.has_feature(abonnement.entreprise_id, FeatureFlag.STANDARD_PDF) is False
