import React from 'react';
import { cn } from '@/lib/utils';
import { Circle, Clock, FlaskConical, Unplug, AlertTriangle, AlertCircle } from 'lucide-react';

export type SourceStatusMode =
  | 'LIVE'
  | 'CACHED'
  | 'SIMULATED'
  | 'CONNECTED'
  | 'PARTIAL'
  | 'NOT_CONNECTED'
  | 'RATE_LIMITED'
  | 'ERROR';

export interface SourceBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  status: SourceStatusMode | string;
  cacheTime?: string;
  className?: string;
}

/**
 * SourceBadge implements the cool ramp specified in the Forensic Lens design direction:
 * - LIVE: solid teal #0E8F9C, dot icon, text "Live"
 * - CONNECTED: solid teal #0E8F9C, dot icon, text "Connected"
 * - CACHED: slate #55627F, clock icon, text "Cached result from HH:MM UTC"
 * - SIMULATED: violet #6D28D9, DASHED border, flask icon, text "Simulated"
 * - PARTIAL: slate/teal #55627F, alert circle, text "Partial"
 * - NOT_CONNECTED: grey #7A8499, hollow plug icon, text "Not connected"
 * - RATE_LIMITED / ERROR: ink-filled with white text, warning-triangle icon, text "Rate limited" / "Source error"
 */
export function SourceBadge({ status, cacheTime, className, ...props }: SourceBadgeProps) {
  const normStatus = (status || 'LIVE').toUpperCase() as SourceStatusMode;

  switch (normStatus) {
    case 'LIVE':
      return (
        <span
          className={cn(
            'inline-flex items-center gap-1.5 px-3 py-1 rounded-pill text-xs font-semibold bg-[#0E8F9C]/10 text-[#09636C] dark:text-[#0E8F9C] border border-[#0E8F9C]/30',
            className
          )}
          {...props}
        >
          <Circle className="w-2 h-2 fill-[#0E8F9C] text-[#0E8F9C] shrink-0" aria-hidden="true" />
          <span>Live</span>
        </span>
      );

    case 'CONNECTED':
      return (
        <span
          className={cn(
            'inline-flex items-center gap-1.5 px-3 py-1 rounded-pill text-xs font-semibold bg-[#0E8F9C]/10 text-[#09636C] dark:text-[#0E8F9C] border border-[#0E8F9C]/30',
            className
          )}
          {...props}
        >
          <Circle className="w-2 h-2 fill-[#0E8F9C] text-[#0E8F9C] shrink-0" aria-hidden="true" />
          <span>Connected</span>
        </span>
      );

    case 'CACHED':
      return (
        <span
          className={cn(
            'inline-flex items-center gap-1.5 px-3 py-1 rounded-pill text-xs font-medium bg-[#55627F]/10 text-[#55627F] dark:text-[#A0AEC0] border border-[#55627F]/25',
            className
          )}
          {...props}
        >
          <Clock className="w-3.5 h-3.5 text-current shrink-0" aria-hidden="true" />
          <span>{cacheTime ? `Cached result from ${cacheTime}` : 'Cached result from 05:12 UTC'}</span>
        </span>
      );

    case 'SIMULATED':
      return (
        <span
          className={cn(
            'inline-flex items-center gap-1.5 px-3 py-1 rounded-pill text-xs font-medium bg-[#6D28D9]/10 text-[#6D28D9] dark:text-[#C4B5FD] border border-dashed border-[#6D28D9]/50 font-mono',
            className
          )}
          {...props}
        >
          <FlaskConical className="w-3.5 h-3.5 text-current shrink-0" aria-hidden="true" />
          <span>Simulated</span>
        </span>
      );

    case 'PARTIAL':
      return (
        <span
          className={cn(
            'inline-flex items-center gap-1.5 px-3 py-1 rounded-pill text-xs font-medium bg-[#55627F]/10 text-[#55627F] dark:text-[#A0AEC0] border border-[#55627F]/30',
            className
          )}
          {...props}
        >
          <AlertCircle className="w-3.5 h-3.5 text-current shrink-0" aria-hidden="true" />
          <span>Partial</span>
        </span>
      );

    case 'NOT_CONNECTED':
      return (
        <span
          className={cn(
            'inline-flex items-center gap-1.5 px-3 py-1 rounded-pill text-xs font-semibold bg-[#7A8499]/10 text-[#474F5E] dark:text-[#CBD5E0] border border-[#7A8499]/30',
            className
          )}
          {...props}
        >
          <Unplug className="w-3.5 h-3.5 text-current shrink-0" aria-hidden="true" />
          <span>Not connected</span>
        </span>
      );

    case 'RATE_LIMITED':
      return (
        <span
          className={cn(
            'inline-flex items-center gap-1.5 px-3 py-1 rounded-pill text-xs font-medium bg-ink text-surface dark:bg-ink dark:text-canvas border border-ink shadow-sm',
            className
          )}
          {...props}
        >
          <AlertTriangle className="w-3.5 h-3.5 text-surface dark:text-canvas shrink-0" aria-hidden="true" />
          <span>Rate limited</span>
        </span>
      );

    case 'ERROR':
    default:
      return (
        <span
          className={cn(
            'inline-flex items-center gap-1.5 px-3 py-1 rounded-pill text-xs font-medium bg-ink text-surface dark:bg-ink dark:text-canvas border border-ink shadow-sm',
            className
          )}
          {...props}
        >
          <AlertTriangle className="w-3.5 h-3.5 text-surface dark:text-canvas shrink-0" aria-hidden="true" />
          <span>Source error</span>
        </span>
      );
  }
}
