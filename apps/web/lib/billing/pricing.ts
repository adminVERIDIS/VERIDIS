export type PlanType = "essential" | "professional" | "enterprise";
export type BillingInterval = "month" | "year";

export interface PricingPlan {
  name: string;
  slug: PlanType;
  priceAnnual: number;
  priceMonthly: number;
  description: string;
  target: string;
  features: string[];
  limitations: string[];
  cta: string;
  recommended?: boolean;
  stripePriceId: string;
  stripePriceIdMonthly?: string;
}

export interface SelectedPrice {
  plan: PricingPlan;
  interval: BillingInterval;
}

export const pricingPlans: PricingPlan[] = [
  {
    name: "Essential",
    slug: "essential",
    priceAnnual: 3600,
    priceMonthly: 375,
    description: "Le socle CSRD pour une premiere evaluation documentee.",
    target: "250-499 salaries",
    features: [
      "Wizard de conformite basique",
      "1 rapport CSRD par an",
      "PDF standard",
      "1 utilisateur",
      "Support email 48h",
    ],
    limitations: ["Pas de benchmark sectoriel", "Pas d'acces API"],
    cta: "Commencer essai gratuit",
    stripePriceId: process.env.NEXT_PUBLIC_STRIPE_PRICE_ESSENTIAL_YEAR ?? "",
    stripePriceIdMonthly: process.env.NEXT_PUBLIC_STRIPE_PRICE_ESSENTIAL_MONTH ?? "",
  },
  {
    name: "Professional",
    slug: "professional",
    priceAnnual: 7200,
    priceMonthly: 750,
    description: "Pour piloter plusieurs sites avec benchmark et support renforce.",
    target: "500-999 salaries",
    features: [
      "3 rapports CSRD par an",
      "3 utilisateurs",
      "Multi-sites",
      "Benchmark sectoriel",
      "Support chat",
    ],
    limitations: ["Pas de white-label PDF", "Pas d'acces API"],
    cta: "Commencer essai gratuit",
    recommended: true,
    stripePriceId: process.env.NEXT_PUBLIC_STRIPE_PRICE_PROFESSIONAL_YEAR ?? "",
    stripePriceIdMonthly: process.env.NEXT_PUBLIC_STRIPE_PRICE_PROFESSIONAL_MONTH ?? "",
  },
  {
    name: "Enterprise",
    slug: "enterprise",
    priceAnnual: 14400,
    priceMonthly: 1500,
    description: "Pour une gouvernance CSRD avancee avec API et accompagnement.",
    target: "1000+ salaries",
    features: [
      "Rapports illimites",
      "10 utilisateurs",
      "Acces API",
      "PDF white-label",
      "SLA 4h et onboarding call",
    ],
    limitations: [],
    cta: "Commencer essai gratuit",
    stripePriceId: process.env.NEXT_PUBLIC_STRIPE_PRICE_ENTERPRISE_YEAR ?? "",
    stripePriceIdMonthly: process.env.NEXT_PUBLIC_STRIPE_PRICE_ENTERPRISE_MONTH ?? "",
  },
];

export function getPlanPriceId(plan: PricingPlan, isAnnual: boolean): string {
  return isAnnual ? plan.stripePriceId : plan.stripePriceIdMonthly ?? "";
}

export function findPlanByPriceId(priceId: string): SelectedPrice | null {
  for (const plan of pricingPlans) {
    if (plan.stripePriceId === priceId) {
      return { plan, interval: "year" };
    }

    if (plan.stripePriceIdMonthly === priceId) {
      return { plan, interval: "month" };
    }
  }

  return null;
}

export function getAllowedPriceIds(): string[] {
  return pricingPlans.flatMap((plan) =>
    [plan.stripePriceId, plan.stripePriceIdMonthly].filter(
      (priceId): priceId is string => Boolean(priceId),
    ),
  );
}

export function formatEuro(amount: number): string {
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(amount);
}
