"use client";

import { Check, Sparkles, X } from "lucide-react";
import { motion } from "framer-motion";

import { formatEuro, getPlanPriceId, type PricingPlan } from "../../lib/billing/pricing";

export interface PricingCardProps {
  plan: PricingPlan;
  isAnnual: boolean;
  isLoading?: boolean;
  onSelect: () => void;
}

export function PricingCard({ plan, isAnnual, isLoading = false, onSelect }: PricingCardProps) {
  const price = isAnnual ? plan.priceAnnual : plan.priceMonthly;
  const annualEquivalent = isAnnual ? plan.priceAnnual : plan.priceMonthly * 12;
  const priceId = getPlanPriceId(plan, isAnnual);
  const intervalLabel = isAnnual ? "/an" : "/mois";
  const ctaLabel = isLoading ? "Ouverture Stripe..." : plan.cta;

  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: plan.recommended ? -4 : 0 }}
      transition={{ duration: 0.24, ease: "easeOut" }}
      className={[
        "flex h-full flex-col rounded-lg border bg-white p-6 shadow-sm",
        "focus-within:ring-2 focus-within:ring-emerald-500",
        plan.recommended
          ? "border-emerald-500 shadow-xl"
          : "border-slate-200 hover:border-slate-300",
      ].join(" ")}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-slate-950">{plan.name}</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">{plan.description}</p>
        </div>

        {plan.recommended ? (
          <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
            <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
            Le plus choisi
          </span>
        ) : null}
      </div>

      <div className="mt-6">
        <div className="flex items-end gap-2">
          <motion.strong
            key={`${plan.slug}-${isAnnual ? "year" : "month"}`}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="font-mono text-4xl font-bold tabular-nums text-slate-950"
          >
            {formatEuro(price)}
          </motion.strong>
          <span className="pb-1 text-sm font-medium text-slate-500">{intervalLabel}</span>
        </div>
        <p className="mt-2 text-sm text-slate-500">
          soit {formatEuro(annualEquivalent)}/an, essai gratuit 14 jours
        </p>
      </div>

      <div className="mt-5 rounded-md bg-slate-50 px-4 py-3 text-sm text-slate-700">
        Cible : {plan.target}
      </div>

      <ul className="mt-6 space-y-3 text-sm text-slate-700">
        {plan.features.map((feature) => (
          <li key={feature} className="flex gap-3">
            <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" aria-hidden="true" />
            <span>{feature}</span>
          </li>
        ))}
      </ul>

      {plan.limitations.length > 0 ? (
        <ul className="mt-5 space-y-3 text-sm text-slate-500">
          {plan.limitations.map((limitation) => (
            <li key={limitation} className="flex gap-3">
              <X className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" aria-hidden="true" />
              <span>{limitation}</span>
            </li>
          ))}
        </ul>
      ) : null}

      <button
        type="button"
        disabled={!priceId || isLoading}
        onClick={onSelect}
        className={[
          "mt-7 inline-flex w-full items-center justify-center rounded-md px-4 py-3",
          "text-sm font-semibold text-white transition-colors",
          "bg-emerald-600 hover:bg-emerald-700",
          "focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2",
          "disabled:cursor-not-allowed disabled:bg-slate-300",
        ].join(" ")}
      >
        {ctaLabel}
      </button>
    </motion.article>
  );
}
