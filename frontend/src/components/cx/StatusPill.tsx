import React from 'react';
import { cn } from '@/lib/utils';
import { Eye, Clock, XCircle, HelpCircle } from 'lucide-react';

export type FindingStatusType =
  | 'NEW'
  | 'IN_REVIEW'
  | 'CONFIRMED_SUSPICIOUS'
  | 'DISMISSED_FALSE_POSITIVE'
  | 'INCONCLUSIVE';

export interface StatusPillProps extends React.HTMLAttributes<HTMLSpanElement> {
  status: FindingStatusType | string;
  className?: string;
}

export function StatusPill({ status, className, ...props }: StatusPillProps) {
  const normStatus = (status || 'NEW').toUpperCase() as FindingStatusType;

  switch (normStatus) {
    case 'CONFIRMED_SUSPICIOUS':
      return (
        <span
          className={cn(
            'inline-flex items-center gap-1.5 px-3 py-0.5 rounded-pill text-xs font-semibold bg-[#A4123F]/10 text-[#A4123F] dark:text-[#FEB2B2] border border-[#A4123F]/30',
            className
          )}
          {...props}
        >
          <AlertCircleIcon className="w-3.5 h-3.5 shrink-0" />
          <span>Confirmed suspicious by analyst</span>
        </span>
      );

    case 'DISMISSED_FALSE_POSITIVE':
      return (
        <span
          className={cn(
            'inline-flex items-center gap-1.5 px-3 py-0.5 rounded-pill text-xs font-medium bg-surface-2 text-ink-muted border border-hairline',
            className
          )}
          {...props}
        >
          <XCircle className="w-3.5 h-3.5 shrink-0" />
          <span>Dismissed (false positive)</span>
        </span>
      );

    case 'IN_REVIEW':
      return (
        <span
          className={cn(
            'inline-flex items-center gap-1.5 px-3 py-0.5 rounded-pill text-xs font-medium bg-[#55627F]/10 text-[#55627F] dark:text-[#A0AEC0] border border-[#55627F]/20',
            className
          )}
          {...props}
        >
          <Clock className="w-3.5 h-3.5 shrink-0" />
          <span>In review</span>
        </span>
      );

    case 'INCONCLUSIVE':
      return (
        <span
          className={cn(
            'inline-flex items-center gap-1.5 px-3 py-0.5 rounded-pill text-xs font-medium bg-surface-2 text-ink-muted border border-hairline',
            className
          )}
          {...props}
        >
          <HelpCircle className="w-3.5 h-3.5 shrink-0" />
          <span>Inconclusive</span>
        </span>
      );

    case 'NEW':
    default:
      return (
        <span
          className={cn(
            'inline-flex items-center gap-1.5 px-3 py-0.5 rounded-pill text-xs font-medium bg-lens/10 text-lens border border-lens/20',
            className
          )}
          {...props}
        >
          <Eye className="w-3.5 h-3.5 shrink-0" />
          <span>New candidate for review</span>
        </span>
      );
  }
}

function AlertCircleIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}
