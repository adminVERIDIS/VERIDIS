"use client";

import { KeyboardEvent } from "react";
import { ChevronRight } from "lucide-react";

export interface FunnelStep {
  name: string;
  count: number;
  conversionRate: number;
  dropOffReasons?: string[];
}

export interface FunnelChartProps {
  steps: FunnelStep[];
  onStepClick?: (step: FunnelStep) => void;
}

const numberFormatter = new Intl.NumberFormat("fr-FR", {
  maximumFractionDigits: 0,
});

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function formatRate(value: number) {
  return `${value.toFixed(value < 10 ? 1 : 0)}%`;
}

export function FunnelChart({ steps, onStepClick }: FunnelChartProps) {
  const maxCount = Math.max(...steps.map((step) => step.count), 1);
  const firstCount = steps[0]?.count ?? 0;

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>, step: FunnelStep) {
    if (!onStepClick) {
      return;
    }

    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onStepClick(step);
    }
  }

  return (
    <section
      className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm sm:p-5"
      aria-labelledby="analytics-funnel-title"
    >
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 id="analytics-funnel-title" className="text-lg font-semibold text-slate-950">
            Funnel acquisition
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Visiteurs, activation document, valeur experimentee, conversion payante.
          </p>
        </div>
        <p className="font-mono text-sm tabular-nums text-slate-600">
          Global {firstCount > 0 ? formatRate(((steps.at(-1)?.count ?? 0) / firstCount) * 100) : "0%"}
        </p>
      </div>

      <div className="mt-5 space-y-3">
        {steps.map((step, index) => {
          const width = clamp((step.count / maxCount) * 100, 16, 100);
          const globalRate = firstCount > 0 ? (step.count / firstCount) * 100 : 0;

          return (
            <div
              key={step.name}
              role={onStepClick ? "button" : "group"}
              tabIndex={onStepClick ? 0 : undefined}
              onClick={() => onStepClick?.(step)}
              onKeyDown={(event) => handleKeyDown(event, step)}
              className={[
                "rounded-md border border-slate-200 bg-slate-50 p-3 outline-none transition-colors",
                onStepClick ? "cursor-pointer hover:border-slate-300 focus-visible:ring-2 focus-visible:ring-emerald-500" : "",
              ].join(" ")}
              aria-label={`${step.name}: ${numberFormatter.format(step.count)}, conversion ${formatRate(step.conversionRate)}`}
            >
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-slate-900">
                    {index + 1}. {step.name}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {formatRate(step.conversionRate)} etape precedente - {formatRate(globalRate)} global
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <span className="font-mono text-sm font-semibold tabular-nums text-slate-950">
                    {numberFormatter.format(step.count)}
                  </span>
                  {onStepClick ? <ChevronRight className="h-4 w-4 text-slate-400" aria-hidden="true" /> : null}
                </div>
              </div>

              <div className="mt-3 h-4 overflow-hidden rounded-full bg-white" aria-hidden="true">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-emerald-600 via-sky-600 to-slate-700"
                  style={{ width: `${width}%` }}
                />
              </div>

              {step.dropOffReasons && step.dropOffReasons.length > 0 ? (
                <ul className="mt-3 flex flex-wrap gap-2 text-xs text-slate-600">
                  {step.dropOffReasons.map((reason) => (
                    <li key={reason} className="rounded-md border border-slate-200 bg-white px-2 py-1">
                      {reason}
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          );
        })}
      </div>
    </section>
  );
}
