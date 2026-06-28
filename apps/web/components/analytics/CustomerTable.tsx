"use client";

import { useMemo, useState } from "react";
import { ArrowDownUp, FileText, Mail, Search, UserRoundCheck } from "lucide-react";

export type UUID = string;
export type PlanType = "essential" | "professional" | "enterprise";
export type CustomerStatus = "trial_active" | "active" | "past_due" | "cancelled" | "churned";
export type HealthScore = "green" | "yellow" | "red";

export interface EntrepriseSummary {
  raisonSociale: string;
  siren: string;
}

export interface CustomerRow {
  id: UUID;
  entreprise: EntrepriseSummary;
  plan: PlanType;
  mrr: number;
  scoreMoyen: number | null;
  status: CustomerStatus;
  lastActivityAt: Date;
  prochaineEcheance: Date;
  healthScore: HealthScore;
}

export interface CustomerTableProps {
  customers: CustomerRow[];
  onViewCustomer?: (customer: CustomerRow) => void;
  onEmailCustomer?: (customer: CustomerRow) => void;
  onViewReports?: (customer: CustomerRow) => void;
}

type SortKey = "entreprise" | "plan" | "mrr" | "scoreMoyen" | "status" | "lastActivityAt" | "prochaineEcheance";
type SortOrder = "asc" | "desc";

const PAGE_SIZE = 50;

const currencyFormatter = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});

const dateFormatter = new Intl.DateTimeFormat("fr-FR", {
  day: "2-digit",
  month: "short",
  year: "numeric",
});

const planLabels: Record<PlanType, string> = {
  essential: "Essential",
  professional: "Pro",
  enterprise: "Enterprise",
};

const statusLabels: Record<CustomerStatus, string> = {
  trial_active: "Trial active",
  active: "Active",
  past_due: "Past due",
  cancelled: "Cancelled",
  churned: "Churned",
};

const healthClasses: Record<HealthScore, string> = {
  green: "bg-emerald-50 text-emerald-700 border-emerald-200",
  yellow: "bg-amber-50 text-amber-700 border-amber-200",
  red: "bg-red-50 text-red-700 border-red-200",
};

function compareCustomers(a: CustomerRow, b: CustomerRow, sortKey: SortKey, sortOrder: SortOrder) {
  const direction = sortOrder === "asc" ? 1 : -1;
  let result = 0;

  if (sortKey === "entreprise") {
    result = a.entreprise.raisonSociale.localeCompare(b.entreprise.raisonSociale);
  } else if (sortKey === "lastActivityAt" || sortKey === "prochaineEcheance") {
    result = a[sortKey].getTime() - b[sortKey].getTime();
  } else {
    const left = a[sortKey] ?? -1;
    const right = b[sortKey] ?? -1;
    result = typeof left === "number" && typeof right === "number"
      ? left - right
      : String(left).localeCompare(String(right));
  }

  return result * direction;
}

export function CustomerTable({
  customers,
  onViewCustomer,
  onEmailCustomer,
  onViewReports,
}: CustomerTableProps) {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<CustomerStatus | "all">("all");
  const [plan, setPlan] = useState<PlanType | "all">("all");
  const [sortKey, setSortKey] = useState<SortKey>("mrr");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");
  const [page, setPage] = useState(1);

  const filteredCustomers = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

    return customers
      .filter((customer) => {
        const matchesStatus = status === "all" || customer.status === status;
        const matchesPlan = plan === "all" || customer.plan === plan;
        const matchesQuery =
          normalizedQuery.length === 0 ||
          customer.entreprise.raisonSociale.toLowerCase().includes(normalizedQuery) ||
          customer.entreprise.siren.includes(normalizedQuery);

        return matchesStatus && matchesPlan && matchesQuery;
      })
      .sort((a, b) => compareCustomers(a, b, sortKey, sortOrder));
  }, [customers, plan, query, sortKey, sortOrder, status]);

  const pageCount = Math.max(Math.ceil(filteredCustomers.length / PAGE_SIZE), 1);
  const visibleCustomers = filteredCustomers.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  function setSort(nextKey: SortKey) {
    if (nextKey === sortKey) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortKey(nextKey);
      setSortOrder("desc");
    }
  }

  return (
    <section
      className="rounded-lg border border-slate-200 bg-white shadow-sm"
      aria-labelledby="analytics-customers-title"
    >
      <div className="border-b border-slate-200 p-4 sm:p-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 id="analytics-customers-title" className="text-lg font-semibold text-slate-950">
              Clients et revenus
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Liste triable pour identifier expansion, risque churn et echeances CSRD.
            </p>
          </div>

          <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_160px_160px] lg:w-[620px]">
            <label className="relative block">
              <span className="sr-only">Rechercher une entreprise ou un SIREN</span>
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
              <input
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  setPage(1);
                }}
                className="h-10 w-full rounded-md border border-slate-200 bg-slate-50 pl-9 pr-3 text-sm text-slate-900 outline-none transition-colors placeholder:text-slate-400 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
                placeholder="Rechercher..."
              />
            </label>

            <select
              value={status}
              onChange={(event) => {
                setStatus(event.target.value as CustomerStatus | "all");
                setPage(1);
              }}
              className="h-10 rounded-md border border-slate-200 bg-slate-50 px-3 text-sm text-slate-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
              aria-label="Filtrer par statut"
            >
              <option value="all">Tous statuts</option>
              {Object.entries(statusLabels).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>

            <select
              value={plan}
              onChange={(event) => {
                setPlan(event.target.value as PlanType | "all");
                setPage(1);
              }}
              className="h-10 rounded-md border border-slate-200 bg-slate-50 px-3 text-sm text-slate-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
              aria-label="Filtrer par plan"
            >
              <option value="all">Tous plans</option>
              {Object.entries(planLabels).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-[980px] w-full border-collapse text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
            <tr>
              {[
                ["entreprise", "Entreprise"],
                ["plan", "Plan"],
                ["mrr", "MRR"],
                ["scoreMoyen", "Score moyen"],
                ["status", "Statut"],
                ["lastActivityAt", "Derniere activite"],
                ["prochaineEcheance", "Echeance CSRD"],
              ].map(([key, label]) => (
                <th key={key} scope="col" className="px-4 py-3 font-semibold">
                  <button
                    type="button"
                    onClick={() => setSort(key as SortKey)}
                    className="inline-flex items-center gap-1 rounded px-1 py-0.5 text-left outline-none hover:text-slate-900 focus-visible:ring-2 focus-visible:ring-emerald-500"
                  >
                    {label}
                    <ArrowDownUp className="h-3.5 w-3.5" aria-hidden="true" />
                  </button>
                </th>
              ))}
              <th scope="col" className="px-4 py-3 font-semibold">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {visibleCustomers.map((customer) => (
              <tr key={customer.id} className="bg-white hover:bg-slate-50">
                <td className="px-4 py-4">
                  <div className="font-semibold text-slate-950">{customer.entreprise.raisonSociale}</div>
                  <div className="mt-1 font-mono text-xs tabular-nums text-slate-500">
                    SIREN {customer.entreprise.siren}
                  </div>
                </td>
                <td className="px-4 py-4">
                  <span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-semibold text-slate-700">
                    {planLabels[customer.plan]}
                  </span>
                </td>
                <td className="px-4 py-4 font-mono font-semibold tabular-nums text-slate-950">
                  {currencyFormatter.format(customer.mrr)}
                </td>
                <td className="px-4 py-4">
                  {customer.scoreMoyen === null ? (
                    <span className="text-slate-400">Non evalue</span>
                  ) : (
                    <span className="font-mono tabular-nums text-slate-800">{customer.scoreMoyen}%</span>
                  )}
                </td>
                <td className="px-4 py-4">
                  <span className={`rounded-md border px-2 py-1 text-xs font-semibold ${healthClasses[customer.healthScore]}`}>
                    {statusLabels[customer.status]}
                  </span>
                </td>
                <td className="px-4 py-4 text-slate-600">
                  {dateFormatter.format(customer.lastActivityAt)}
                </td>
                <td className="px-4 py-4 text-slate-600">
                  {dateFormatter.format(customer.prochaineEcheance)}
                </td>
                <td className="px-4 py-4">
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => onViewCustomer?.(customer)}
                      className="inline-flex h-9 w-9 items-center justify-center rounded-md text-slate-500 outline-none hover:bg-slate-100 hover:text-slate-900 focus-visible:ring-2 focus-visible:ring-emerald-500"
                      aria-label={`Voir la fiche ${customer.entreprise.raisonSociale}`}
                    >
                      <UserRoundCheck className="h-4 w-4" aria-hidden="true" />
                    </button>
                    <button
                      type="button"
                      onClick={() => onEmailCustomer?.(customer)}
                      className="inline-flex h-9 w-9 items-center justify-center rounded-md text-slate-500 outline-none hover:bg-slate-100 hover:text-slate-900 focus-visible:ring-2 focus-visible:ring-emerald-500"
                      aria-label={`Envoyer un email a ${customer.entreprise.raisonSociale}`}
                    >
                      <Mail className="h-4 w-4" aria-hidden="true" />
                    </button>
                    <button
                      type="button"
                      onClick={() => onViewReports?.(customer)}
                      className="inline-flex h-9 w-9 items-center justify-center rounded-md text-slate-500 outline-none hover:bg-slate-100 hover:text-slate-900 focus-visible:ring-2 focus-visible:ring-emerald-500"
                      aria-label={`Voir les rapports ${customer.entreprise.raisonSociale}`}
                    >
                      <FileText className="h-4 w-4" aria-hidden="true" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {visibleCustomers.length === 0 ? (
          <div className="border-t border-slate-100 px-4 py-12 text-center text-sm text-slate-500">
            Aucun client ne correspond aux filtres.
          </div>
        ) : null}
      </div>

      <div className="flex flex-col gap-3 border-t border-slate-200 px-4 py-3 text-sm text-slate-600 sm:flex-row sm:items-center sm:justify-between">
        <span>
          {filteredCustomers.length} clients - page {page} / {pageCount}
        </span>
        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={page === 1}
            onClick={() => setPage((current) => Math.max(current - 1, 1))}
            className="rounded-md border border-slate-200 px-3 py-2 font-semibold text-slate-700 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Precedent
          </button>
          <button
            type="button"
            disabled={page === pageCount}
            onClick={() => setPage((current) => Math.min(current + 1, pageCount))}
            className="rounded-md border border-slate-200 px-3 py-2 font-semibold text-slate-700 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Suivant
          </button>
        </div>
      </div>
    </section>
  );
}
