"use client";

import * as React from "react";
import { motion, useReducedMotion } from "framer-motion";
import { Info } from "lucide-react";

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

export type ScoreGaugeSize = "sm" | "md" | "lg";
export type ScoreGaugeStatus = "non_conforme" | "partiel" | "conforme";

export interface ScoreGaugeProps {
  score: number;
  max?: number;
  size?: ScoreGaugeSize;
  showLabel?: boolean;
  showDetail?: boolean;
  animate?: boolean;
  onClick?: () => void;
}

type GaugeStatusConfig = {
  label: string;
  shortLabel: string;
  color: string;
  badgeClassName: string;
  tooltip: string;
};

export const SCORE_GAUGE_COPY = {
  label: "Conformité CSRD",
  scorePrefix: "Score VERIDIS",
  tooltipAriaLabel: "Expliquer le calcul du score",
} as const;
const VIEWBOX_SIZE = 300;
const CENTER = 150;
const RADIUS = 104;
const START_ANGLE = 135;
const SWEEP_ANGLE = 270;

const SIZE_CONFIG: Record<ScoreGaugeSize, { diameter: number; stroke: number }> = {
  sm: { diameter: 120, stroke: 10 },
  md: { diameter: 200, stroke: 14 },
  lg: { diameter: 280, stroke: 16 },
};

const STATUS_CONFIG: Record<ScoreGaugeStatus, GaugeStatusConfig> = {
  non_conforme: {
    label: "Non conforme",
    shortLabel: "Risque élevé",
    color: "#EF4444",
    badgeClassName:
      "border-red-200 bg-red-50 text-red-700 dark:border-red-900 dark:bg-red-950/50 dark:text-red-200",
    tooltip:
      "Score inférieur à 50 : exigences ESRS critiques absentes, partielles ou insuffisamment prouvées.",
  },
  partiel: {
    label: "Partiel",
    shortLabel: "À compléter",
    color: "#F59E0B",
    badgeClassName:
      "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900 dark:bg-amber-950/50 dark:text-amber-200",
    tooltip:
      "Score entre 50 et 79 : conformité engagée, mais preuves, exigences ou contrôles restent à renforcer.",
  },
  conforme: {
    label: "Conforme",
    shortLabel: "Prêt audit",
    color: "#10B981",
    badgeClassName:
      "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/50 dark:text-emerald-200",
    tooltip:
      "Score de 80 ou plus : exigences principales couvertes avec un niveau de preuve exploitable en revue.",
  },
};

const TICKS = Array.from({ length: 11 }, (_, index) => index * 10);
const LABEL_TICKS = [0, 25, 50, 75, 100] as const;

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function normalizeScore(score: number, max: number) {
  if (!Number.isFinite(score) || !Number.isFinite(max) || max <= 0) {
    return { value: 0, percent: 0 };
  }

  const value = clamp(score, 0, max);
  return {
    value,
    percent: clamp((value / max) * 100, 0, 100),
  };
}

function resolveStatus(percent: number): ScoreGaugeStatus {
  if (percent >= 80) return "conforme";
  if (percent >= 50) return "partiel";
  return "non_conforme";
}

function polarToCartesian(angle: number, radius = RADIUS) {
  const radians = (angle * Math.PI) / 180;

  return {
    x: CENTER + radius * Math.cos(radians),
    y: CENTER + radius * Math.sin(radians),
  };
}

function describeArc(startAngle: number, endAngle: number, radius = RADIUS) {
  const start = polarToCartesian(startAngle, radius);
  const end = polarToCartesian(endAngle, radius);
  const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";

  return [
    "M",
    start.x,
    start.y,
    "A",
    radius,
    radius,
    0,
    largeArcFlag,
    1,
    end.x,
    end.y,
  ].join(" ");
}

function formatScore(value: number) {
  return Number.isInteger(value) ? value.toString() : value.toFixed(1);
}

function GaugeSvg({
  percent,
  displayValue,
  status,
  size,
  animate,
}: {
  percent: number;
  displayValue: string;
  status: GaugeStatusConfig;
  size: ScoreGaugeSize;
  animate: boolean;
}) {
  const reducedMotion = useReducedMotion();
  const shouldAnimate = animate && !reducedMotion;
  const stroke = SIZE_CONFIG[size].stroke;
  const endAngle = START_ANGLE + (percent / 100) * SWEEP_ANGLE;
  const needleEnd = polarToCartesian(endAngle, 78);
  const cursor = polarToCartesian(endAngle, RADIUS);
  const initialEnd = polarToCartesian(START_ANGLE, 78);
  const initialCursor = polarToCartesian(START_ANGLE, RADIUS);

  return (
    <svg
      viewBox={`0 0 ${VIEWBOX_SIZE} ${VIEWBOX_SIZE}`}
      className="block h-full w-full overflow-visible"
      aria-hidden="true"
    >
      <path
        d={describeArc(START_ANGLE, START_ANGLE + SWEEP_ANGLE)}
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth={stroke}
        className="text-slate-100 dark:text-slate-800"
      />

      <motion.path
        d={describeArc(START_ANGLE, endAngle)}
        fill="none"
        stroke={status.color}
        strokeLinecap="round"
        strokeWidth={stroke}
        initial={{ pathLength: shouldAnimate ? 0 : 1 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: shouldAnimate ? 0.9 : 0, ease: [0.22, 1, 0.36, 1] }}
      />

      {TICKS.map((tick) => {
        const angle = START_ANGLE + (tick / 100) * SWEEP_ANGLE;
        const outer = polarToCartesian(angle, 124);
        const inner = polarToCartesian(angle, tick % 20 === 0 ? 113 : 117);

        return (
          <line
            key={tick}
            x1={inner.x}
            y1={inner.y}
            x2={outer.x}
            y2={outer.y}
            stroke="currentColor"
            strokeLinecap="round"
            strokeWidth={tick % 20 === 0 ? 2 : 1}
            className="text-slate-300 dark:text-slate-700"
          />
        );
      })}

      {LABEL_TICKS.map((tick) => {
        const angle = START_ANGLE + (tick / 100) * SWEEP_ANGLE;
        const label = polarToCartesian(angle, 142);

        return (
          <text
            key={tick}
            x={label.x}
            y={label.y}
            textAnchor="middle"
            dominantBaseline="middle"
            className="fill-slate-500 text-[13px] font-medium dark:fill-slate-400"
          >
            {tick}
          </text>
        );
      })}

      <motion.line
        x1={CENTER}
        y1={CENTER}
        x2={needleEnd.x}
        y2={needleEnd.y}
        stroke={status.color}
        strokeLinecap="round"
        strokeWidth={5}
        initial={{
          x2: shouldAnimate ? initialEnd.x : needleEnd.x,
          y2: shouldAnimate ? initialEnd.y : needleEnd.y,
        }}
        animate={{ x2: needleEnd.x, y2: needleEnd.y }}
        transition={{
          type: "spring",
          stiffness: shouldAnimate ? 120 : 1000,
          damping: shouldAnimate ? 18 : 100,
        }}
      />
      <circle cx={CENTER} cy={CENTER} r={10} fill="white" className="dark:fill-slate-950" />
      <circle cx={CENTER} cy={CENTER} r={5} fill={status.color} />

      <motion.circle
        cx={cursor.x}
        cy={cursor.y}
        r={7}
        fill={status.color}
        stroke="white"
        strokeWidth={3}
        initial={{
          cx: shouldAnimate ? initialCursor.x : cursor.x,
          cy: shouldAnimate ? initialCursor.y : cursor.y,
        }}
        animate={{ cx: cursor.x, cy: cursor.y }}
        transition={{
          type: "spring",
          stiffness: shouldAnimate ? 120 : 1000,
          damping: shouldAnimate ? 18 : 100,
        }}
      />

      <motion.text
        x={CENTER}
        y={CENTER + 48}
        textAnchor="middle"
        dominantBaseline="middle"
        initial={{ scale: shouldAnimate ? 0 : 1, opacity: shouldAnimate ? 0 : 1 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ delay: shouldAnimate ? 0.16 : 0, duration: shouldAnimate ? 0.32 : 0 }}
        style={{
          fontFamily:
            '"JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
          transformOrigin: `${CENTER}px ${CENTER + 48}px`,
        }}
        className="fill-slate-950 text-[42px] font-bold tabular-nums dark:fill-slate-50"
      >
        {displayValue}
      </motion.text>
    </svg>
  );
}

/**
 * ScoreGauge affiche le score CSRD VERIDIS sous forme de jauge SVG 270 degres,
 * avec aiguille animee et statut conforme / partiel / non conforme.
 */
export function ScoreGauge({
  score,
  max = 100,
  size = "md",
  showLabel = true,
  showDetail = false,
  animate = true,
  onClick,
}: ScoreGaugeProps) {
  const descriptionId = React.useId();
  const safeMax = Number.isFinite(max) && max > 0 ? max : 100;
  const normalized = normalizeScore(score, safeMax);
  const percent = normalized.percent;
  const displayValue = formatScore(normalized.value);
  const statusKey = resolveStatus(percent);
  const status = STATUS_CONFIG[statusKey];
  const diameter = SIZE_CONFIG[size].diameter;
  const ariaValueText = `${displayValue} sur ${safeMax}, ${status.label}`;
  const handleKeyDown = React.useCallback(
    (event: React.KeyboardEvent<HTMLDivElement>) => {
      if (!onClick) return;

      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        onClick();
      }
    },
    [onClick],
  );

  return (
    <div
      role="meter"
      aria-label={SCORE_GAUGE_COPY.label}
      aria-valuemin={0}
      aria-valuemax={safeMax}
      aria-valuenow={Number(displayValue)}
      aria-valuetext={ariaValueText}
      aria-describedby={descriptionId}
      aria-haspopup={onClick ? "dialog" : undefined}
      data-status={statusKey}
      onClick={onClick}
      onKeyDown={handleKeyDown}
      tabIndex={onClick ? 0 : undefined}
      className={cn(
        "inline-flex min-w-0 flex-col items-center gap-3 rounded-md border border-slate-200 bg-white p-4 text-slate-950 shadow-sm",
        "dark:border-slate-800 dark:bg-slate-950 dark:text-slate-50",
        onClick &&
          "transition-colors hover:border-slate-300 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 focus-visible:ring-offset-2 dark:hover:border-slate-700 dark:hover:bg-slate-900",
      )}
      style={{ width: `min(100%, ${diameter + 36}px)` }}
    >
      <p id={descriptionId} className="sr-only">
        Score CSRD calcule sur les exigences ESRS validees, la qualite des
        preuves et les incoherences detectees. Seuils: 0 a 49 non conforme, 50
        a 79 partiel, 80 a 100 conforme.
      </p>

      <div style={{ width: diameter, height: diameter }} className="max-w-full">
        <GaugeSvg
          percent={percent}
          displayValue={displayValue}
          status={status}
          size={size}
          animate={animate}
        />
      </div>

      {showLabel ? (
        <div className="space-y-1 text-center">
          <p className="text-sm font-semibold text-slate-900 dark:text-slate-50">
            {SCORE_GAUGE_COPY.label}
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {SCORE_GAUGE_COPY.scorePrefix} sur {safeMax}
          </p>
        </div>
      ) : null}

      {showDetail ? (
        <div className="flex max-w-full items-center justify-center gap-2">
          <span
            className={cn(
              "inline-flex min-w-0 items-center rounded-md border px-2.5 py-1 text-xs font-medium",
              status.badgeClassName,
            )}
          >
            {status.label}
          </span>

          <TooltipProvider delayDuration={150}>
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-500 transition-colors hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-400 dark:hover:bg-slate-900 dark:hover:text-slate-50"
                  aria-label={SCORE_GAUGE_COPY.tooltipAriaLabel}
                  onClick={(event) => event.stopPropagation()}
                >
                  <Info className="h-4 w-4" aria-hidden="true" />
                </button>
              </TooltipTrigger>
              <TooltipContent className="max-w-[18rem] text-sm leading-6">
                <p className="font-medium">{status.shortLabel}</p>
                <p className="text-muted-foreground">{status.tooltip}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      ) : null}
    </div>
  );
}

export { STATUS_CONFIG as SCORE_GAUGE_STATUS_CONFIG };
