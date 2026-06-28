"use client";

import { useEffect, useState } from "react";
import { CreditCard, ExternalLink, FileText } from "lucide-react";

import { formatEuro, type PlanType } from "../../../../lib/billing/pricing";

type SubscriptionStatus =
  | "trialing"
  | "active"
  | "past_due"
  | "canceled"
  | "inactive"
  | "unpaid";

interface Invoice {
  id: string;
  amountPaid: number;
  currency: string;
  hostedInvoiceUrl: string | null;
  invoicePdf: string | null;
  status: string | null;
  created: string;
}

interface BillingInfo {
  plan: PlanType | "free";
  status: SubscriptionStatus;
  currentPeriodEnd: string | null;
  trialEnd: string | null;
  invoices: Invoice[];
}

const statusLabels: Record<SubscriptionStatus, string> = {
  trialing: "Essai actif",
  active: "Actif",
  past_due: "Paiement en retard",
  canceled: "Annule",
  inactive: "Inactif",
  unpaid: "Impayee",
};

function formatDate(value: string | null): string {
  if (!value) return "Non disponible";
  return new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium" }).format(new Date(value));
}

export default function BillingPage() {
  const [billingInfo, setBillingInfo] = useState<BillingInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPortalLoading, setIsPortalLoading] = useState(false);

  useEffect(() => {
    void fetch("/api/billing/current")
      .then(async (response) => {
        const data = (await response.json()) as BillingInfo & { error?: string };
        if (!response.ok) throw new Error(data.error ?? "Facturation indisponible.");
        setBillingInfo(data);
      })
      .catch((billingError) => {
        const message =
          billingError instanceof Error ? billingError.message : "Facturation indisponible.";
        setError(message);
      });
  }, []);

  async function openPortal() {
    setIsPortalLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/stripe/portal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ returnUrl: window.location.href }),
      });
      const data = (await response.json()) as { url?: string; error?: string };
      if (!response.ok || !data.url) {
        throw new Error(data.error ?? "Portail Stripe indisponible.");
      }
      window.location.assign(data.url);
    } catch (portalError) {
      const message = portalError instanceof Error ? portalError.message : "Erreur Stripe.";
      setError(message);
      setIsPortalLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 text-slate-950 sm:px-6 lg:px-8">
      <section className="mx-auto flex max-w-5xl flex-col gap-6">
        <div>
          <p className="text-sm font-semibold uppercase text-emerald-700">Facturation</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-normal">Abonnement VERIDIS</h1>
        </div>

        {error ? (
          <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        ) : null}

        <section className="grid gap-4 md:grid-cols-3">
          <article className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm md:col-span-2">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm text-slate-500">Plan actuel</p>
                <h2 className="mt-2 text-2xl font-semibold capitalize">
                  {billingInfo?.plan ?? "Chargement"}
                </h2>
              </div>
              <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-sm font-semibold text-emerald-700">
                {billingInfo ? statusLabels[billingInfo.status] : "Chargement"}
              </span>
            </div>

            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              <div className="rounded-md bg-slate-50 p-4">
                <span className="text-sm text-slate-500">Prochaine facture</span>
                <strong className="mt-1 block text-lg">{formatDate(billingInfo?.currentPeriodEnd ?? null)}</strong>
              </div>
              <div className="rounded-md bg-slate-50 p-4">
                <span className="text-sm text-slate-500">Fin essai</span>
                <strong className="mt-1 block text-lg">{formatDate(billingInfo?.trialEnd ?? null)}</strong>
              </div>
            </div>
          </article>

          <article className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <CreditCard className="h-5 w-5 text-emerald-700" aria-hidden="true" />
            <h2 className="mt-4 text-lg font-semibold">Gestion self-serve</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Modifier le plan, telecharger les factures ou annuler depuis Stripe Customer Portal.
            </p>
            <button
              type="button"
              onClick={() => void openPortal()}
              disabled={isPortalLoading}
              className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-md bg-emerald-600 px-4 py-3 text-sm font-semibold text-white hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 disabled:bg-slate-300"
            >
              {isPortalLoading ? "Ouverture..." : "Modifier mon plan"}
              <ExternalLink className="h-4 w-4" aria-hidden="true" />
            </button>
          </article>
        </section>

        <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold">Historique factures</h2>
          <div className="mt-4 grid gap-3">
            {billingInfo?.invoices.map((invoice) => (
              <article
                key={invoice.id}
                className="flex flex-col gap-3 rounded-md border border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="flex items-start gap-3">
                  <FileText className="mt-1 h-4 w-4 text-slate-500" aria-hidden="true" />
                  <div>
                    <strong className="block text-sm text-slate-950">
                      {formatEuro(invoice.amountPaid / 100)}
                    </strong>
                    <span className="text-sm text-slate-500">
                      {formatDate(invoice.created)} - {invoice.status ?? "statut inconnu"}
                    </span>
                  </div>
                </div>
                {invoice.hostedInvoiceUrl ? (
                  <a
                    href={invoice.hostedInvoiceUrl}
                    className="text-sm font-semibold text-emerald-700 hover:text-emerald-800"
                    target="_blank"
                    rel="noreferrer"
                  >
                    Ouvrir
                  </a>
                ) : null}
              </article>
            )) ?? (
              <div className="rounded-md bg-slate-50 p-4 text-sm text-slate-600">
                Les factures apparaitront ici apres le premier cycle Stripe.
              </div>
            )}
          </div>
        </section>
      </section>
    </main>
  );
}
