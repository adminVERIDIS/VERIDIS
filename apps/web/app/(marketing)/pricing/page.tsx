"use client";

import { useMemo, useState } from "react";
import { ShieldCheck } from "lucide-react";

import { PricingCard } from "../../../components/pricing/PricingCard";
import { getPlanPriceId, pricingPlans, type PricingPlan } from "../../../lib/billing/pricing";

type CheckoutResponse = {
  sessionId: string;
  url: string;
};

const faqItems = [
  {
    question: "L'essai gratuit demande-t-il une carte ?",
    answer:
      "Oui. Stripe collecte la carte au depart pour activer l'essai, mais aucun debit n'est effectue avant la fin des 14 jours.",
  },
  {
    question: "Puis-je annuler avant le prelevement ?",
    answer:
      "Oui. L'annulation se fait depuis le Customer Portal Stripe, sans echange commercial obligatoire.",
  },
  {
    question: "Comment la TVA est-elle geree ?",
    answer:
      "La TVA EU est calculee par Stripe Automatic Tax selon les informations de facturation.",
  },
  {
    question: "Mes donnees CSRD sont-elles exportables ?",
    answer:
      "Oui. Les rapports et donnees de conformite restent exportables depuis l'espace premium.",
  },
  {
    question: "Quel support est inclus ?",
    answer:
      "Essential inclut l'email 48h, Professional ajoute le chat, Enterprise ajoute SLA 4h et onboarding.",
  },
];

export default function PricingPage() {
  const [isAnnual, setIsAnnual] = useState(true);
  const [loadingPriceId, setLoadingPriceId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const savingsLabel = useMemo(() => "Economisez 20% avec l'annuel", []);

  async function startCheckout(plan: PricingPlan) {
    const priceId = getPlanPriceId(plan, isAnnual);
    if (!priceId) {
      setError("Price ID Stripe manquant pour ce plan.");
      return;
    }

    setError(null);
    setLoadingPriceId(priceId);

    try {
      const origin = window.location.origin;
      const response = await fetch("/api/stripe/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          priceId,
          successUrl: `${origin}/upload?checkout=success`,
          cancelUrl: `${origin}/pricing?checkout=cancelled`,
        }),
      });

      const data = (await response.json()) as Partial<CheckoutResponse> & { error?: string };
      if (!response.ok || !data.url) {
        throw new Error(data.error ?? "Impossible d'ouvrir Stripe Checkout.");
      }

      window.location.assign(data.url);
    } catch (checkoutError) {
      const message =
        checkoutError instanceof Error ? checkoutError.message : "Erreur Stripe inattendue.";
      setError(message);
      setLoadingPriceId(null);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-10 text-slate-950 sm:px-6 lg:px-8">
      <section className="mx-auto flex max-w-6xl flex-col gap-8">
        <div className="max-w-3xl">
          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-white px-3 py-1 text-sm font-medium text-emerald-700">
            <ShieldCheck className="h-4 w-4" aria-hidden="true" />
            Essai 14 jours, carte demandee, 0 euro jour 1
          </div>
          <h1 className="mt-5 text-4xl font-semibold tracking-normal text-slate-950 sm:text-5xl">
            Choisissez le plan VERIDIS adapte a votre echeance CSRD
          </h1>
          <p className="mt-5 text-lg leading-8 text-slate-600">
            Pricing clair, annulation facile, factures Stripe et TVA automatique pour un achat
            self-serve sans friction.
          </p>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div
            className="inline-flex w-fit rounded-md border border-slate-200 bg-white p-1"
            role="group"
            aria-label="Choisir l'intervalle de facturation"
          >
            <button
              type="button"
              onClick={() => setIsAnnual(false)}
              className={[
                "rounded px-4 py-2 text-sm font-semibold transition-colors",
                isAnnual ? "text-slate-500 hover:text-slate-900" : "bg-slate-950 text-white",
              ].join(" ")}
              aria-pressed={!isAnnual}
            >
              Mensuel
            </button>
            <button
              type="button"
              onClick={() => setIsAnnual(true)}
              className={[
                "rounded px-4 py-2 text-sm font-semibold transition-colors",
                isAnnual ? "bg-slate-950 text-white" : "text-slate-500 hover:text-slate-900",
              ].join(" ")}
              aria-pressed={isAnnual}
            >
              Annuel
            </button>
          </div>
          <p className="text-sm font-medium text-emerald-700">{savingsLabel}</p>
        </div>

        {error ? (
          <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        ) : null}

        <div className="grid gap-5 lg:grid-cols-3">
          {pricingPlans.map((plan) => {
            const priceId = getPlanPriceId(plan, isAnnual);
            return (
              <PricingCard
                key={plan.slug}
                plan={plan}
                isAnnual={isAnnual}
                isLoading={loadingPriceId === priceId}
                onSelect={() => void startCheckout(plan)}
              />
            );
          })}
        </div>

        <section className="rounded-lg border border-slate-200 bg-white p-6">
          <h2 className="text-2xl font-semibold text-slate-950">Questions frequentes</h2>
          <div className="mt-5 divide-y divide-slate-200">
            {faqItems.map((item) => (
              <details key={item.question} className="group py-4">
                <summary className="cursor-pointer text-base font-semibold text-slate-900 outline-none focus-visible:ring-2 focus-visible:ring-emerald-500">
                  {item.question}
                </summary>
                <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">{item.answer}</p>
              </details>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}
