import React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

export type StatusType =
  | 'LIVE'
  | 'CACHED'
  | 'SIMULATED'
  | 'NOT_CONNECTED'
  | 'RATE_LIMITED'
  | 'ERROR';

export type SeverityType = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

const badgeVariants = cva(
  'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold tracking-wide transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
  {
    variants: {
      variant: {
        default: 'bg-primary/20 text-primary-foreground border border-primary/30',
        outline: 'border border-border text-foreground',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

interface StatusBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  status: StatusType;
  cacheTime?: string;
  className?: string;
}

export function StatusBadge({ status, cacheTime, className, ...props }: StatusBadgeProps) {
  let badgeStyle = '';
  let label = status as string;

  switch (status) {
    case 'LIVE':
      // Distinct Emerald/Teal
      badgeStyle = 'bg-emerald-950/70 text-emerald-300 border border-emerald-500/40';
      label = 'LIVE';
      break;
    case 'CACHED':
      // Distinct Cyan/Indigo
      badgeStyle = 'bg-cyan-950/70 text-cyan-300 border border-cyan-500/40';
      label = cacheTime ? `CACHED (${cacheTime})` : 'CACHED';
      break;
    case 'SIMULATED':
      // Distinct Violet/Purple with DASHED border per contract
      badgeStyle = 'bg-purple-950/70 text-purple-300 border-2 border-dashed border-purple-400/60 font-mono';
      label = 'SIMULATED';
      break;
    case 'NOT_CONNECTED':
      // Neutral Slate/Zinc
      badgeStyle = 'bg-zinc-800/80 text-zinc-300 border border-zinc-600/50';
      label = 'NOT_CONNECTED';
      break;
    case 'RATE_LIMITED':
      // Outline amber
      badgeStyle = 'bg-amber-950/60 text-amber-300 border border-amber-500/50';
      label = 'RATE_LIMITED';
      break;
    case 'ERROR':
      // Rose/Ruby
      badgeStyle = 'bg-rose-950/70 text-rose-300 border border-rose-500/50';
      label = 'ERROR';
      break;
  }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium',
        badgeStyle,
        className
      )}
      {...props}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current opacity-80" aria-hidden="true" />
      <span>{label}</span>
    </span>
  );
}

interface SeverityBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  severity: SeverityType | string;
  className?: string;
}

export function SeverityBadge({ severity, className, ...props }: SeverityBadgeProps) {
  const sev = (severity || 'LOW').toUpperCase() as SeverityType;
  let badgeStyle = '';

  // Severity colours are strictly distinct from source status colours
  switch (sev) {
    case 'LOW':
      badgeStyle = 'bg-sky-950/70 text-sky-300 border border-sky-500/40';
      break;
    case 'MEDIUM':
      badgeStyle = 'bg-amber-950/80 text-amber-300 border border-amber-500/50';
      break;
    case 'HIGH':
      badgeStyle = 'bg-orange-950/80 text-orange-300 border border-orange-500/60';
      break;
    case 'CRITICAL':
      badgeStyle = 'bg-red-950/90 text-red-300 border border-red-500/70 font-bold';
      break;
    default:
      badgeStyle = 'bg-zinc-800 text-zinc-300 border border-zinc-700';
  }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider',
        badgeStyle,
        className
      )}
      {...props}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current" aria-hidden="true" />
      <span>{sev}</span>
    </span>
  );
}

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}
