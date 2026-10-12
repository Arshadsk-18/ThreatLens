import React from 'react';
import { cn } from '@/lib/utils';

export interface StatTileProps {
  label: string;
  value: React.ReactNode;
  hint?: string;
  icon?: React.ReactNode;
  badge?: React.ReactNode;
  className?: string;
}

export function StatTile({ label, value, hint, icon, badge, className }: StatTileProps) {
  return (
    <div
      className={cn(
        'rounded-panel border border-hairline bg-surface p-5 flex flex-col justify-between space-y-3 transition-colors',
        className
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-ink-muted leading-tight">
          {label}
        </span>
        {badge ? badge : icon ? <div className="text-ink-muted">{icon}</div> : null}
      </div>

      <div className="space-y-1">
        <div className="font-display font-bold text-3xl text-ink tracking-tight">
          {value}
        </div>
        {hint && <p className="text-xs text-ink-muted prose-lens leading-normal">{hint}</p>}
      </div>
    </div>
  );
}
