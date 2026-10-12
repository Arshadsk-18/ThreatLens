import React from 'react';
import { cn } from '@/lib/utils';
import { Unplug } from 'lucide-react';

export interface NotConnectedStateProps {
  platform: string;
  reason?: string;
  className?: string;
}

export function NotConnectedState({
  platform,
  reason = 'Requires platform API developer access. Not queried.',
  className,
}: NotConnectedStateProps) {
  return (
    <div
      role="status"
      className={cn(
        'rounded-nested border border-hairline bg-surface-2 p-6 text-center flex flex-col items-center justify-center space-y-2',
        className
      )}
    >
      <div className="w-10 h-10 rounded-pill bg-canvas border border-hairline flex items-center justify-center text-[#7A8499]">
        <Unplug className="w-4 h-4" aria-hidden="true" />
      </div>
      <h4 className="font-display font-semibold text-sm text-ink">
        {platform}: not connected
      </h4>
      <p className="text-xs text-ink-muted prose-lens leading-relaxed">
        {reason}
      </p>
      <span className="font-mono text-[11px] px-2.5 py-0.5 rounded-pill bg-canvas border border-hairline text-ink-muted">
        Source status: NOT_CONNECTED
      </span>
    </div>
  );
}
