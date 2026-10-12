import React from 'react';
import { cn } from '@/lib/utils';

export interface GaugeProps {
  value: number; // 0 to 100
  max?: number;
  label?: string;
  subtitle?: string;
  hideProbabilityNote?: boolean;
  size?: number; // width in px
  className?: string;
}

export function Gauge({
  value,
  max = 100,
  label = 'Risk score',
  subtitle,
  hideProbabilityNote = false,
  size = 180,
  className,
}: GaugeProps) {
  const clamped = Math.max(0, Math.min(max, value));
  const fraction = clamped / max;

  // Semicircle arc parameters
  const strokeWidth = 14;
  const radius = (size - strokeWidth) / 2;
  const circumference = Math.PI * radius; // Half circumference for semicircle
  const strokeDashoffset = circumference * (1 - fraction);

  // Determine warm severity color
  let strokeColor = 'hsl(var(--lens))';
  if (fraction >= 0.75) {
    strokeColor = 'hsl(var(--severity-critical))';
  } else if (fraction >= 0.5) {
    strokeColor = 'hsl(var(--severity-high))';
  } else if (fraction >= 0.25) {
    strokeColor = 'hsl(var(--severity-medium))';
  }

  return (
    <div className={cn('flex flex-col items-center justify-center text-center', className)}>
      <div className="relative" style={{ width: size, height: size / 2 + 18 }}>
        <svg
          width={size}
          height={size / 2 + strokeWidth}
          viewBox={`0 0 ${size} ${size / 2 + strokeWidth}`}
          className="overflow-visible"
        >
          {/* Background Track Arc */}
          <path
            d={`M ${strokeWidth / 2} ${size / 2} A ${radius} ${radius} 0 0 1 ${size - strokeWidth / 2} ${size / 2}`}
            fill="none"
            stroke="hsl(var(--hairline))"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />

          {/* Active Value Arc */}
          <path
            d={`M ${strokeWidth / 2} ${size / 2} A ${radius} ${radius} 0 0 1 ${size - strokeWidth / 2} ${size / 2}`}
            fill="none"
            stroke={strokeColor}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className="transition-all duration-500 ease-out"
          />
        </svg>

        {/* Center Metric Display */}
        <div
          className="absolute inset-0 flex flex-col items-center justify-end"
          style={{ bottom: 2 }}
        >
          <span className="font-display font-bold text-3xl text-ink leading-none">
            {Math.round(clamped)}
          </span>
          <span className="text-[11px] font-mono text-ink-muted leading-tight mt-0.5">
            / {max}
          </span>
        </div>
      </div>

      <div className="mt-2 space-y-0.5">
        <span className="text-xs font-medium text-ink block">{label}</span>
        {subtitle ? (
          <span className="text-[11px] text-ink-muted block">{subtitle}</span>
        ) : !hideProbabilityNote && label !== "Review progress" ? (
          <span className="text-[11px] text-ink-muted italic block">
            (not a probability)
          </span>
        ) : null}
      </div>
    </div>
  );
}
