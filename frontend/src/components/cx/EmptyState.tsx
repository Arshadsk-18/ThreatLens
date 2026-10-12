import React from 'react';
import { cn } from '@/lib/utils';
import { Inbox } from 'lucide-react';

export interface EmptyStateProps {
  title?: string;
  description: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  title = 'No candidates for review',
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      role="status"
      className={cn(
        'rounded-panel border border-hairline bg-surface p-10 text-center flex flex-col items-center justify-center space-y-3',
        className
      )}
    >
      <div className="w-12 h-12 rounded-pill bg-surface-2 border border-hairline flex items-center justify-center text-ink-muted">
        <Inbox className="w-5 h-5" aria-hidden="true" />
      </div>
      <h3 className="font-display font-semibold text-base text-ink">
        {title}
      </h3>
      <p className="text-sm text-ink-muted prose-lens leading-relaxed">
        {description}
      </p>
      {action && <div className="pt-2">{action}</div>}
    </div>
  );
}
