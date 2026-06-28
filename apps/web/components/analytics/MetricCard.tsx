"use client";

import { KeyboardEvent } from "react";
import { AlertTriangle, ArrowDownRight, ArrowUpRight, Target } from "lucide-react";
import { motion } from "framer-motion";

export type MetricFormat = "currency" | "percent" | "number" | "duration";

export interface AlertCondition {
  operator: "gt" | "lt";
  value: number;
}

export interface MetricCardProps {
  title: string;
  value: number;
  previousValue: number;
  format: MetricFormat;
  sparklineData: number[];
  target?: number;
  alertThreshold?: AlertCondition;
  onClick?: () => void;
  description?: string;
  favorableDirection?: "up" | "down";
}

const numberFormatter = new Intl.NumberFormat("fr-FR", {
  maximumFractionDigits: 0,
});

const currencyFormatter = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function formatValue(value: number, format: MetricFormat) {
  if (format === "currency") {
    return currencyFormatter.format(value);
  }

  if (format === "percent") {
    return `${value.toFixed(value < 10 ? 1 : 0)}%`;
  }

  if (format === "duration") {
    if (value < 60) {
      return `${Math.round(value)}s`;
    }
    const minutes = value / 60;
    return `${minutes.toFixed(minutes < 10 ? 1 : 0)} min`;
  }

  return numberFormatter.format(value);
}

function buildSparklinePath(points: number[], width = 220, height = 54) {
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

function isAlerting(value: number, alertThreshold?: AlertCondition) {
  if (!alertThreshold) {
    return false;
  }

  return alertThreshold.operator === "gt"
    ? value > alertThreshold.value
    : value < alertThreshold.value;
}

export function MetricCard({
  title,
  value,
  previousValue,
  format,
  sparklineData,
  target,
  alertThreshold,
  onClick,
  description,
  favorableDirection = "up",
}: MetricCardProps) {
  const delta = value - previousValue;
  const deltaPercent = previousValue === 0 ? 0 : (delta / Math.abs(previousValue)) * 100;
  const isPositive = delta >= 0;
  const isGoodDelta = favorableDirection === "up" ? isPositive : !isPositive;
  const alerting = isAlerting(value, alertThreshold);
  const progress = target ? clamp((value / target) * 100, 0, 100) : null;
  const sparkPath = buildSparklinePath(sparklineData);

  function handleKeyDown(event: KeyboardEvent<HTMLElement>) {
    if (!onClick) {
      return;
    }

    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onClick();
    }
  }

  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, ease: "easeOut" }}
      onClick={onClick}
      onKeyDown={handleKeyDown}
      role={onClick ? "button" : "group"}
      tabIndex={onClick ? 0 : undefined}
      aria-label={`${title}: ${formatValue(value, format)}`}
      className={[
        "relative flex min-h-[190px] flex-col rounded-lg border bg-white p-4 shadow-sm",
        "outline-none transition-colors sm:p-5",
        onClick ? "cursor-pointer hover:border-slate-300 focus-visible:ring-2 focus-visible:ring-emerald-500" : "",
        alerting
          ? "border-red-300 shadow-red-100 ring-1 ring-red-100 motion-safe:animate-pulse"
          : "border-slate-200",
      ].join(" ")}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-slate-600">{title}</p>
          {description ? <p className="mt-1 text-xs leading-5 text-slate-500">{description}</p> : null}
        </div>
        {alerting ? (
          <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-red-200 bg-red-50 text-red-600">
            <AlertTriangle className="h-4 w-4" aria-hidden="true" />
            <span className="sr-only">Alerte active</span>
          </span>
        ) : null}
      </div>

      <div className="mt-4 flex items-end justify-between gap-3">
        <strong className="font-mono text-3xl font-semibold tabular-nums text-slate-950">
          {formatValue(value, format)}
        </strong>
        <span
          className={[
            "inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-semibold",
            isGoodDelta ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700",
          ].join(" ")}
          aria-label={`Variation ${deltaPercent.toFixed(1)} pour cent`}
        >
          {isPositive ? (
            <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
          ) : (
            <ArrowDownRight className="h-3.5 w-3.5" aria-hidden="true" />
          )}
          {Math.abs(deltaPercent).toFixed(1)}%
        </span>
      </div>

      <svg
        className="mt-5 h-14 w-full overflow-visible"
        viewBox="0 0 220 54"
        role="img"
        aria-label={`Tendance recente de ${title}`}
        preserveAspectRatio="none"
      >
        <path d="M 0 53.5 L 220 53.5" stroke="rgb(226 232 240)" strokeWidth="1" />
        {sparkPath ? (
          <path
            d={sparkPath}
            fill="none"
            stroke={alerting ? "rgb(220 38 38)" : "rgb(5 150 105)"}
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="3"
            vectorEffect="non-scaling-stroke"
          />
        ) : null}
      </svg>

      {progress !== null ? (
        <div className="mt-auto pt-4">
          <div className="mb-2 flex items-center justify-between gap-3 text-xs text-slate-500">
            <span className="inline-flex items-center gap-1 font-medium">
              <Target className="h-3.5 w-3.5" aria-hidden="true" />
              Objectif
            </span>
            <span className="font-mono tabular-nums">{Math.round(progress)}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-slate-100" aria-hidden="true">
            <div className="h-full rounded-full bg-emerald-600" style={{ width: `${progress}%` }} />
          </div>
        </div>
      ) : null}
    </motion.article>
  );
}
