from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol
from uuid import UUID

from models import Abonnement, PlanType, SubscriptionStatus


class FeatureFlag(str, Enum):
    BASIC_WIZARD = "basic_wizard"
    STANDARD_PDF = "standard_pdf"
    EMAIL_SUPPORT = "email_support"
    MULTI_SITE = "multi_site"
    BENCHMARK = "benchmark"
    REALTIME_CHAT = "realtime_chat"
    API_ACCESS = "api_access"
    WHITE_LABEL_PDF = "white_label_pdf"
    SLA_4H = "sla_4h"
    ONBOARDING_CALL = "onboarding_call"


@dataclass(frozen=True)
class PlanLimits:
    plan: PlanType
    max_rapports: int | None
    max_utilisateurs: int
    features: frozenset[FeatureFlag]
    support_label: str


class BillingRepository(Protocol):
    def get_current_abonnement(self, entreprise_id: UUID) -> Abonnement | None:
        ...

    def count_rapports_for_period(self, entreprise_id: UUID, abonnement: Abonnement) -> int:
        ...

    def count_users(self, entreprise_id: UUID) -> int:
        ...


PLAN_LIMITS: dict[PlanType, PlanLimits] = {
    PlanType.ESSENTIAL: PlanLimits(
        plan=PlanType.ESSENTIAL,
        max_rapports=1,
        max_utilisateurs=1,
        features=frozenset(
            {
                FeatureFlag.BASIC_WIZARD,
                FeatureFlag.STANDARD_PDF,
                FeatureFlag.EMAIL_SUPPORT,
            }
        ),
        support_label="email 48h",
    ),
    PlanType.PROFESSIONAL: PlanLimits(
        plan=PlanType.PROFESSIONAL,
        max_rapports=3,
        max_utilisateurs=3,
        features=frozenset(
            {
                FeatureFlag.BASIC_WIZARD,
                FeatureFlag.STANDARD_PDF,
                FeatureFlag.EMAIL_SUPPORT,
                FeatureFlag.MULTI_SITE,
                FeatureFlag.BENCHMARK,
                FeatureFlag.REALTIME_CHAT,
            }
        ),
        support_label="chat",
    ),
    PlanType.ENTERPRISE: PlanLimits(
        plan=PlanType.ENTERPRISE,
        max_rapports=None,
        max_utilisateurs=10,
        features=frozenset(
            {
                FeatureFlag.BASIC_WIZARD,
                FeatureFlag.STANDARD_PDF,
                FeatureFlag.EMAIL_SUPPORT,
                FeatureFlag.MULTI_SITE,
                FeatureFlag.BENCHMARK,
                FeatureFlag.REALTIME_CHAT,
                FeatureFlag.API_ACCESS,
                FeatureFlag.WHITE_LABEL_PDF,
                FeatureFlag.SLA_4H,
                FeatureFlag.ONBOARDING_CALL,
            }
        ),
        support_label="SLA 4h",
    ),
    PlanType.FREE: PlanLimits(
        plan=PlanType.FREE,
        max_rapports=0,
        max_utilisateurs=1,
        features=frozenset(),
        support_label="read-only",
    ),
}

ACTIVE_STATUSES = {
    SubscriptionStatus.TRIAL_ACTIVE,
    SubscriptionStatus.ACTIVE,
    SubscriptionStatus.PAST_DUE,
}


class EntitlementService:
    """
    Controle les acces premium depuis la DB locale, sans appel Stripe synchrone.
    """

    def __init__(self, repository: BillingRepository) -> None:
        self.repository = repository

    def can_create_rapport(self, entreprise_id: UUID) -> bool:
        abonnement = self._active_abonnement(entreprise_id)
        if abonnement is None:
            return False

        limit = abonnement.max_rapports
        if limit is None:
            return True

        used = self.repository.count_rapports_for_period(entreprise_id, abonnement)
        return used < limit

    def can_add_user(self, entreprise_id: UUID) -> bool:
        abonnement = self._active_abonnement(entreprise_id)
        if abonnement is None:
            return False

        used = self.repository.count_users(entreprise_id)
        return used < abonnement.max_utilisateurs

    def has_feature(self, entreprise_id: UUID, feature: FeatureFlag) -> bool:
        abonnement = self._active_abonnement(entreprise_id)
        if abonnement is None:
            return False

        cached_value = abonnement.features.get(feature.value)
        if isinstance(cached_value, bool):
            return cached_value

        return feature in self.get_plan_limits(abonnement.plan).features

    def get_plan_limits(self, plan: PlanType) -> PlanLimits:
        return PLAN_LIMITS.get(plan, PLAN_LIMITS[PlanType.FREE])

    def _active_abonnement(self, entreprise_id: UUID) -> Abonnement | None:
        abonnement = self.repository.get_current_abonnement(entreprise_id)
        if abonnement is None:
            return None
        return abonnement if abonnement.status in ACTIVE_STATUSES else None
