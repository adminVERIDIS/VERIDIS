"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Bell,
  CalendarDays,
  CheckCircle2,
  Clock,
  RefreshCw,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { motion } from "framer-motion";

import { CustomerTable, type CustomerRow } from "../../../components/analytics/CustomerTable";
import { FunnelChart, type FunnelStep } from "../../../components/analytics/FunnelChart";
import { MetricCard, type AlertCondition, type MetricFormat } from "../../../components/analytics/MetricCard";

type DateRangeKey = "7d" | "30d" | "90d" | "ytd" | "custom";

interface DateRange {
  key: DateRangeKey;
  label: string;
  start: string;
  end: string;
}

interface MRRCompositionItem {
  label: string;
  value: number;
  tone: "positive" | "negative" | "neutral";
}

interface MRRAnalytics {
  value: number;
  previousValue: number;
  target: number;
  deadlineLabel: string;
  sparklineData: number[];
  composition: MRRCompositionItem[];
}

interface DashboardMetric {
  id: string;
  title: string;
  value: number;
  previousValue: number;
  format: MetricFormat;
  sparklineData: number[];
  target?: number;
  alertThreshold?: AlertCondition;
  favorableDirection?: "up" | "down";
  description: string;
}

interface FounderAlert {
  id: string;
  severity: "critical" | "warning" | "info";
  metric: string;
  message: string;
  action: string;
  channel: "email" | "slack" | "in_app";
}

interface AnalyticsPayload {
  mrr: MRRAnalytics;
  primaryMetrics: DashboardMetric[];
  productMetrics: DashboardMetric[];
  technicalMetrics: DashboardMetric[];
  funnel: FunnelStep[];
  customers: CustomerRow[];
  alerts: FounderAlert[];
  generatedAt: string;
}

const rangeOptions: Array<{ key: DateRangeKey; label: string; days?: number }> = [
  { key: "7d", label: "7j", days: 7 },
  { key: "30d", label: "30j", days: 30 },
  { key: "90d", label: "90j", days: 90 },
  { key: "ytd", label: "YTD" },
  { key: "custom", label: "Custom" },
];

const currencyFormatter = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});

const dateTimeFormatter = new Intl.DateTimeFormat("fr-FR", {
  day: "2-digit",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

function isoDate(date: Date) {
  return date.toISOString().slice(0, 10);
}

function defaultRange(): DateRange {
  const end = new Date();
  const start = new Date(end);
  start.setDate(start.getDate() - 30);
  return {
    key: "30d",
    label: "30j",
    start: isoDate(start),
    end: isoDate(end),
  };
}

function buildRange(key: DateRangeKey, current: DateRange): DateRange {
  const now = new Date();
  const option = rangeOptions.find((range) => range.key === key);

  if (key === "custom") {
    return { ...current, key, label: "Custom" };
  }

  if (key === "ytd") {
    return {
      key,
      label: "YTD",
      start: isoDate(new Date(now.getFullYear(), 0, 1)),
      end: isoDate(now),
    };
  }

  const start = new Date(now);
  start.setDate(start.getDate() - (option?.days ?? 30));

  return {
    key,
    label: option?.label ?? "30j",
    start: isoDate(start),
    end: isoDate(now),
  };
}

function useAnalyticsResource<T>(
  endpoint: string,
  fallback: T,
  normalize: (value: T) => T = (value) => value,
) {
  const [data, setData] = useState<T>(fallback);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [updatedAt, setUpdatedAt] = useState<Date>(new Date());

  useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();

    async function load() {
      setIsRefreshing(true);
      try {
        const response = await fetch(endpoint, {
          credentials: "include",
          signal: controller.signal,
          headers: { Accept: "application/json" },
        });

        if (!response.ok) {
          throw new Error(`API analytics ${response.status}`);
        }

        const payload = (await response.json()) as T;
        if (isMounted) {
          setData(normalize(payload));
          setError(null);
          setUpdatedAt(new Date());
        }
      } catch (loadError) {
        if (isMounted && !controller.signal.aborted) {
          setError(loadError instanceof Error ? loadError.message : "API analytics indisponible");
        }
      } finally {
        if (isMounted) {
          setIsRefreshing(false);
        }
      }
    }

    void load();
    const interval = window.setInterval(() => void load(), 30_000);

    return () => {
      isMounted = false;
      controller.abort();
      window.clearInterval(interval);
    };
  }, [endpoint, normalize]);

  return { data, error, isRefreshing, updatedAt };
}

function normalizeAnalyticsPayload(payload: AnalyticsPayload): AnalyticsPayload {
  return {
    ...payload,
    customers: payload.customers.map((customer) => ({
      ...customer,
      lastActivityAt: new Date(customer.lastActivityAt),
      prochaineEcheance: new Date(customer.prochaineEcheance),
    })),
  };
}

function metric(
  id: string,
  title: string,
  value: number,
  previousValue: number,
  format: MetricFormat,
  description: string,
  target?: number,
  alertThreshold?: AlertCondition,
  favorableDirection: "up" | "down" = "up",
): DashboardMetric {
  const base = value || 1;
  return {
    id,
    title,
    value,
    previousValue,
    format,
    description,
    target,
    alertThreshold,
    favorableDirection,
    sparklineData: Array.from({ length: 30 }, (_, index) => {
      const wave = Math.sin(index / 3) * base * 0.035;
      const drift = (index - 15) * base * 0.006;
      return Math.max(base + wave + drift, 0);
    }),
  };
}

const fallbackPayload: AnalyticsPayload = {
  generatedAt: new Date().toISOString(),
  mrr: {
    value: 12_450,
    previousValue: 10_650,
    target: 20_000,
    deadlineLabel: "J-45",
    sparklineData: [4100, 4600, 5100, 5700, 6200, 6900, 7200, 8100, 8900, 9700, 10650, 12450],
    composition: [
      { label: "New MRR", value: 2400, tone: "positive" },
      { label: "Expansion", value: 650, tone: "positive" },
      { label: "Contraction", value: -300, tone: "negative" },
      { label: "Churn", value: -950, tone: "negative" },
    ],
  },
  primaryMetrics: [
    metric("new-trials", "Nouveaux trials", 12, 8, "number", "Inscriptions essai 14j sur 7j glissant.", 10, { operator: "lt", value: 5 }),
    metric("trial-to-paid", "Trial-to-paid", 22.4, 18.1, "percent", "Conversion essai vers payant.", 20, { operator: "lt", value: 15 }),
    metric("churn", "Churn mensuel", 4.1, 6.3, "percent", "Clients perdus sur mois glissant.", 5, { operator: "gt", value: 8 }, "down"),
    metric("cac", "CAC", 420, 520, "currency", "Cout acquisition client.", 500, { operator: "gt", value: 800 }, "down"),
    metric("ltv", "LTV", 8200, 7600, "currency", "Lifetime value estimee.", 7000, { operator: "lt", value: 5000 }),
    metric("ltv-cac", "LTV/CAC", 4.1, 3.2, "number", "Rentabilite acquisition.", 3, { operator: "lt", value: 2 }),
  ],
  productMetrics: [
    metric("activation", "Activation", 64, 57, "percent", "Trials ayant uploade un document.", 60, { operator: "lt", value: 60 }),
    metric("time-to-value", "Time-to-value", 260, 420, "duration", "Inscription vers premier score.", 300, { operator: "gt", value: 300 }, "down"),
    metric("feature-usage", "Feature usage", 83, 79, "percent", "Clients utilisant analyse par mois.", 80, { operator: "lt", value: 80 }),
    metric("nps", "NPS", 44, 38, "number", "Satisfaction in-app survey.", 40, { operator: "lt", value: 40 }),
    metric("support-tickets", "Support tickets", 6.1, 4.3, "number", "Tickets / 100 clients / mois.", 5, { operator: "gt", value: 5 }, "down"),
  ],
  technicalMetrics: [
    metric("uptime-api", "Uptime API", 99.95, 99.91, "percent", "Disponibilite API.", 99.9, { operator: "lt", value: 99.9 }),
    metric("analysis-time", "Temps analyse moyen", 98, 112, "duration", "Moyenne 24h.", 120, { operator: "gt", value: 120 }, "down"),
    metric("errors-500", "Erreurs 500 / jour", 2, 4, "number", "Erreurs serveur sur 24h.", 5, { operator: "gt", value: 5 }, "down"),
    metric("api-p95", "Temps reponse API p95", 540, 410, "duration", "Latence p95 API.", 500, { operator: "gt", value: 500 }, "down"),
  ],
  funnel: [
    { name: "Visiteurs uniques", count: 4200, conversionRate: 100 },
    { name: "Inscriptions wizard", count: 680, conversionRate: 16.2, dropOffReasons: ["preuve valeur tardive", "CTA pricing"] },
    { name: "Trials demarres", count: 210, conversionRate: 30.9 },
    { name: "Documents uploades", count: 134, conversionRate: 63.8, dropOffReasons: ["document introuvable", "format refus"] },
    { name: "Analyses completees", count: 119, conversionRate: 88.8 },
    { name: "Conversions payantes", count: 47, conversionRate: 39.5 },
    { name: "Renouvellements annee 2", count: 18, conversionRate: 38.3 },
  ],
  customers: [
    {
      id: "cst_001",
      entreprise: { raisonSociale: "Ateliers Durand", siren: "552081317" },
      plan: "professional",
      mrr: 249,
      scoreMoyen: 78,
      status: "active",
      lastActivityAt: new Date("2026-06-28T07:42:00Z"),
      prochaineEcheance: new Date("2026-09-30"),
      healthScore: "green",
    },
    {
      id: "cst_002",
      entreprise: { raisonSociale: "Novalia Industrie", siren: "812554301" },
      plan: "enterprise",
      mrr: 990,
      scoreMoyen: 66,
      status: "past_due",
      lastActivityAt: new Date("2026-06-22T16:10:00Z"),
      prochaineEcheance: new Date("2026-07-15"),
      healthScore: "red",
    },
    {
      id: "cst_003",
      entreprise: { raisonSociale: "Greenpack Europe", siren: "443002118" },
      plan: "essential",
      mrr: 99,
      scoreMoyen: null,
      status: "trial_active",
      lastActivityAt: new Date("2026-06-27T12:31:00Z"),
      prochaineEcheance: new Date("2026-12-31"),
      healthScore: "yellow",
    },
  ],
  alerts: [
    {
      id: "mrr-behind",
      severity: "critical",
      metric: "MRR",
      message: "MRR projete sous objectif mensuel de 2 150 EUR.",
      action: "Relancer les prospects chauds et verifier le drop-off trial vers upload.",
      channel: "email",
    },
    {
      id: "support-tickets",
      severity: "warning",
      metric: "Support tickets",
      message: "Tickets au-dessus de la cible sur le mois glissant.",
      action: "Publier un guide upload documents et revoir les erreurs de parsing.",
      channel: "slack",
    },
    {
      id: "api-p95",
      severity: "warning",
      metric: "API p95",
      message: "Latence p95 au-dessus de 500ms sur 24h.",
      action: "Controler requetes dashboard et cache Redis analytics.",
      channel: "slack",
    },
  ],
};

function buildEndpoint(range: DateRange) {
  const params = new URLSearchParams({
    start_date: range.start,
    end_date: range.end,
  });
  return `/api/analytics/dashboard?${params.toString()}`;
}

function formatCurrency(value: number) {
  return currencyFormatter.format(value);
}

function formatSignedCurrency(value: number) {
  const prefix = value >= 0 ? "+" : "-";
  return `${prefix}${formatCurrency(Math.abs(value))}`;
}

function buildSparklinePath(points: number[], width = 420, height = 72) {
  if (points.length === 0) {
    return "";
  }

  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;
  const step = points.length > 1 ? width / (points.length - 1) : width;

  return points
    .map((point, index) => {
      const x = index * step;
      const y = height - ((point - min) / range) * height;
      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
}

function mrrProgress(mrr: MRRAnalytics) {
  return Math.min(Math.max((mrr.value / mrr.target) * 100, 0), 100);
}

function Gauge({ value }: { value: number }) {
  const radius = 58;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;

  return (
    <svg className="h-36 w-36" viewBox="0 0 144 144" role="img" aria-label={`Objectif MRR atteint a ${Math.round(value)} pour cent`}>
      <circle cx="72" cy="72" r={radius} fill="none" stroke="rgb(226 232 240)" strokeWidth="12" />
      <motion.circle
        cx="72"
        cy="72"
        r={radius}
        fill="none"
        stroke="rgb(5 150 105)"
        strokeLinecap="round"
        strokeWidth="12"
        strokeDasharray={circumference}
        initial={{ strokeDashoffset: circumference }}
        animate={{ strokeDashoffset: offset }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        transform="rotate(-90 72 72)"
      />
      <text x="72" y="68" textAnchor="middle" className="fill-slate-950 font-mono text-2xl font-semibold">
        {Math.round(value)}%
      </text>
      <text x="72" y="90" textAnchor="middle" className="fill-slate-500 text-[11px] font-medium">
        objectif
      </text>
    </svg>
  );
}

function severityClasses(severity: FounderAlert["severity"]) {
  if (severity === "critical") {
    return "border-red-200 bg-red-50 text-red-700";
  }
  if (severity === "warning") {
    return "border-amber-200 bg-amber-50 text-amber-700";
  }
  return "border-sky-200 bg-sky-50 text-sky-700";
}

export default function AnalyticsDashboardPage() {
  const [range, setRange] = useState<DateRange>(() => defaultRange());
  const [activeDrilldown, setActiveDrilldown] = useState<string | null>(null);
  const endpoint = useMemo(() => buildEndpoint(range), [range]);
  const { data, error, isRefreshing, updatedAt } = useAnalyticsResource(
    endpoint,
    fallbackPayload,
    normalizeAnalyticsPayload,
  );
  const progress = mrrProgress(data.mrr);
  const mrrDelta = data.mrr.value - data.mrr.previousValue;
  const mrrSparklinePath = buildSparklinePath(data.mrr.sparklineData);

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-5 sm:px-6 lg:px-8">
        <header className="flex flex-col gap-4 border-b border-slate-200 pb-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="inline-flex items-center gap-2 rounded-md border border-emerald-200 bg-white px-3 py-1 text-sm font-semibold text-emerald-700">
              <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
              Admin analytics
            </div>
            <h1 className="mt-3 text-3xl font-semibold tracking-normal text-slate-950 sm:text-4xl">
              Cockpit fondateur VERIDIS
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
              Les metriques vitales pour savoir en 30 secondes quoi corriger aujourd'hui.
            </p>
          </div>

          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Choisir la periode analytics">
              {rangeOptions.map((option) => (
                <button
                  key={option.key}
                  type="button"
                  onClick={() => setRange((current) => buildRange(option.key, current))}
                  className={[
                    "rounded-md border px-3 py-2 text-sm font-semibold outline-none transition-colors focus-visible:ring-2 focus-visible:ring-emerald-500",
                    range.key === option.key
                      ? "border-slate-950 bg-slate-950 text-white"
                      : "border-slate-200 bg-white text-slate-700 hover:border-slate-300",
                  ].join(" ")}
                  aria-pressed={range.key === option.key}
                >
                  {option.label}
                </button>
              ))}
            </div>

            {range.key === "custom" ? (
              <div className="grid gap-2 sm:grid-cols-2">
                <label className="text-xs font-medium text-slate-600">
                  Debut
                  <input
                    type="date"
                    value={range.start}
                    onChange={(event) => setRange((current) => ({ ...current, start: event.target.value }))}
                    className="mt-1 h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm text-slate-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
                  />
                </label>
                <label className="text-xs font-medium text-slate-600">
                  Fin
                  <input
                    type="date"
                    value={range.end}
                    onChange={(event) => setRange((current) => ({ ...current, end: event.target.value }))}
                    className="mt-1 h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm text-slate-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
                  />
                </label>
              </div>
            ) : null}

            <div className="flex items-center gap-2 text-xs text-slate-500">
              <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin" : ""}`} aria-hidden="true" />
              <span>Refresh 30s - {dateTimeFormatter.format(updatedAt)}</span>
            </div>
          </div>
        </header>

        {error ? (
          <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800" role="status">
            API analytics indisponible: affichage du dernier jeu local de securite. {error}
          </div>
        ) : null}

        {activeDrilldown ? (
          <div className="rounded-md border border-sky-200 bg-sky-50 px-4 py-3 text-sm font-medium text-sky-800" role="status">
            Drill-down selectionne: {activeDrilldown}. Les donnees detaillees sont chargees via l'API analytics paginee.
          </div>
        ) : null}

        <section className="grid gap-5 lg:grid-cols-[minmax(0,1.45fr)_minmax(320px,0.55fr)]">
          <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-500">North Star - Monthly Recurring Revenue</p>
                <div className="mt-2 flex flex-wrap items-end gap-3">
                  <strong className="font-mono text-5xl font-semibold tabular-nums text-slate-950">
                    {formatCurrency(data.mrr.value)}
                  </strong>
                  <span
                    className={[
                      "mb-1 inline-flex items-center gap-1 rounded-md px-2 py-1 text-sm font-semibold",
                      mrrDelta >= 0 ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700",
                    ].join(" ")}
                  >
                    {mrrDelta >= 0 ? <TrendingUp className="h-4 w-4" aria-hidden="true" /> : <TrendingDown className="h-4 w-4" aria-hidden="true" />}
                    {formatSignedCurrency(mrrDelta)} vs mois -1
                  </span>
                </div>
                <p className="mt-3 text-sm text-slate-600">
                  Objectif {formatCurrency(data.mrr.target)} ({data.mrr.deadlineLabel})
                </p>
              </div>
              <Gauge value={progress} />
            </div>

            <div className="mt-5">
              <svg
                className="mb-4 h-[72px] w-full"
                viewBox="0 0 420 72"
                preserveAspectRatio="none"
                role="img"
                aria-label="Sparkline MRR des 12 derniers mois"
              >
                <path d="M 0 71.5 L 420 71.5" stroke="rgb(226 232 240)" strokeWidth="1" />
                {mrrSparklinePath ? (
                  <path
                    d={mrrSparklinePath}
                    fill="none"
                    stroke="rgb(5 150 105)"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="3"
                    vectorEffect="non-scaling-stroke"
                  />
                ) : null}
              </svg>
              <div className="h-3 overflow-hidden rounded-full bg-slate-100" aria-hidden="true">
                <div className="h-full rounded-full bg-emerald-600" style={{ width: `${progress}%` }} />
              </div>
              <div className="mt-2 flex justify-between text-xs text-slate-500">
                <span>{Math.round(progress)}% atteint</span>
                <span>{formatCurrency(data.mrr.target - data.mrr.value)} restant</span>
              </div>
            </div>

            <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {data.mrr.composition.map((item) => (
                <div key={item.label} className="rounded-md border border-slate-200 bg-slate-50 p-3">
                  <p className="text-xs font-medium text-slate-500">{item.label}</p>
                  <p
                    className={[
                      "mt-2 font-mono text-lg font-semibold tabular-nums",
                      item.tone === "positive" ? "text-emerald-700" : item.tone === "negative" ? "text-red-700" : "text-slate-950",
                    ].join(" ")}
                  >
                    {formatSignedCurrency(item.value)}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm" aria-labelledby="analytics-alerts-title">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 id="analytics-alerts-title" className="text-lg font-semibold text-slate-950">
                  Alertes actives
                </h2>
                <p className="mt-1 text-sm text-slate-500">Email critique, Slack pour le reste.</p>
              </div>
              <Bell className="h-5 w-5 text-slate-400" aria-hidden="true" />
            </div>

            <div className="mt-4 space-y-3">
              {data.alerts.map((alert) => (
                <article key={alert.id} className={`rounded-md border p-3 ${severityClasses(alert.severity)}`}>
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                    <div>
                      <p className="text-sm font-semibold">{alert.metric}</p>
                      <p className="mt-1 text-sm">{alert.message}</p>
                      <p className="mt-2 text-xs font-semibold uppercase tracking-normal">
                        Action: {alert.action}
                      </p>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </section>
        </section>

        <section aria-labelledby="primary-metrics-title">
          <div className="mb-3 flex items-center gap-2">
            <CalendarDays className="h-4 w-4 text-slate-400" aria-hidden="true" />
            <h2 id="primary-metrics-title" className="text-lg font-semibold text-slate-950">
              Metriques principales
            </h2>
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {data.primaryMetrics.map((item) => (
              <MetricCard key={item.id} {...item} onClick={() => setActiveDrilldown(item.title)} />
            ))}
          </div>
        </section>

        <section aria-labelledby="product-metrics-title">
          <div className="mb-3 flex items-center gap-2">
            <Clock className="h-4 w-4 text-slate-400" aria-hidden="true" />
            <h2 id="product-metrics-title" className="text-lg font-semibold text-slate-950">
              Metriques produit
            </h2>
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            {data.productMetrics.map((item) => (
              <MetricCard key={item.id} {...item} onClick={() => setActiveDrilldown(item.title)} />
            ))}
          </div>
        </section>

        <details className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm open:p-5">
          <summary className="cursor-pointer text-lg font-semibold text-slate-950 outline-none focus-visible:ring-2 focus-visible:ring-emerald-500">
            Metriques techniques
          </summary>
          <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {data.technicalMetrics.map((item) => (
              <MetricCard key={item.id} {...item} onClick={() => setActiveDrilldown(item.title)} />
            ))}
          </div>
        </details>

        <div className="grid gap-5 xl:grid-cols-[420px_minmax(0,1fr)]">
          <FunnelChart steps={data.funnel} onStepClick={(step) => setActiveDrilldown(`Funnel - ${step.name}`)} />
          <CustomerTable
            customers={data.customers}
            onViewCustomer={(customer) => setActiveDrilldown(`Client - ${customer.entreprise.raisonSociale}`)}
            onEmailCustomer={(customer) => setActiveDrilldown(`Email - ${customer.entreprise.raisonSociale}`)}
            onViewReports={(customer) => setActiveDrilldown(`Rapports - ${customer.entreprise.raisonSociale}`)}
          />
        </div>
      </div>
    </main>
  );
}
