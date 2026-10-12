import React from 'react';
import { cn } from '@/lib/utils';
import { ShieldCheck, AlertTriangle, AlertCircle, ShieldAlert } from 'lucide-react';

export type SeverityType = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface SeverityPillProps extends React.HTMLAttributes<HTMLSpanElement> {
  severity: SeverityType | string;
  className?: string;
}

/**
 * SeverityPill implements the warm ramp strictly reserved for finding severity:
 * - Low: soft grey/slate with ShieldCheck icon
 * - Medium: #B7791F with AlertTriangle icon
 * - High: #D9480F with AlertCircle icon
 * - Critical: #A4123F with ShieldAlert icon
 * Carries an icon shape + sentence case text word (never color alone).
 */
export function SeverityPill({ severity, className, ...props }: SeverityPillProps) {
  const normSev = (severity || 'LOW').toUpperCase() as SeverityType;

  switch (normSev) {
    case 'LOW':
      return (
        <span
          className={cn(
            'inline-flex items-center gap-1.5 px-3 py-0.5 rounded-pill text-xs font-medium bg-[#4B5563]/10 text-[#4B5563] dark:text-[#9CA3AF] border border-[#4B5563]/20',
            className
          )}
          {...props}
        >
          <ShieldCheck className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
          <span>Low</span>
        </span>
      );

    case 'MEDIUM':
      return (
        <span
          className={cn(
            'inline-flex items-center gap-1.5 px-3 py-0.5 rounded-pill text-xs font-semibold bg-[#B7791F]/10 text-[#B7791F] dark:text-[#F6E05E] border border-[#B7791F]/30',
            className
          )}
          {...props}
        >
          <AlertTriangle className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
          <span>Medium</span>
        </span>
      );

    case 'HIGH':
      return (
        <span
          className={cn(
            'inline-flex items-center gap-1.5 px-3 py-0.5 rounded-pill text-xs font-semibold bg-[#D9480F]/10 text-[#AF3405] dark:text-[#FBD38D] border border-[#D9480F]/30',
            className
          )}
          {...props}
        >
          <AlertCircle className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
          <span>High</span>
        </span>
      );

    case 'CRITICAL':
      return (
        <span
          className={cn(
            'inline-flex items-center gap-1.5 px-3 py-0.5 rounded-pill text-xs font-bold bg-[#A4123F]/10 text-[#A4123F] dark:text-[#FEB2B2] border border-[#A4123F]/40 shadow-sm',
            className
          )}
          {...props}
        >
          <ShieldAlert className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
          <span>Critical</span>
        </span>
      );
  }
}
