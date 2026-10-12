import React from 'react';
import { cn } from '@/lib/utils';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export interface ErrorStateProps {
  title?: string;
  message: string;
  requestId?: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({
  title = 'Data retrieval error',
  message,
  requestId,
  onRetry,
  className,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        'rounded-panel border border-[#A4123F]/20 bg-[#A4123F]/5 p-8 text-center flex flex-col items-center justify-center space-y-3',
        className
      )}
    >
      <div className="w-12 h-12 rounded-pill bg-[#A4123F]/10 text-[#A4123F] flex items-center justify-center">
        <AlertTriangle className="w-5 h-5" aria-hidden="true" />
      </div>
      <h3 className="font-display font-semibold text-base text-ink">
        {title}
      </h3>
      <p className="text-sm text-ink-muted prose-lens leading-relaxed">
        {message}
      </p>
      {requestId && (
        <span className="font-mono text-xs px-2.5 py-1 rounded-pill bg-surface border border-hairline text-ink-muted">
          Request ID: {requestId}
        </span>
      )}
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 inline-flex items-center gap-1.5 px-4 py-1.5 rounded-pill text-xs font-semibold bg-ink text-surface dark:bg-surface dark:text-ink hover:opacity-90 transition-opacity focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lens"
        >
          <RefreshCw className="w-3.5 h-3.5" aria-hidden="true" />
          <span>Retry request</span>
        </button>
      )}
    </div>
  );
}
