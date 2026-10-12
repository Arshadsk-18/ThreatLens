import React from 'react';
import { cn } from '@/lib/utils';

export interface RiskScoreProps {
  score: number | null | undefined;
  size?: 'sm' | 'md' | 'lg';
  showSubtitle?: boolean;
  className?: string;
}

export function RiskScore({ score, size = 'md', showSubtitle = true, className }: RiskScoreProps) {
  if (score === null || score === undefined) {
    return (
      <div className={cn('space-y-0.5', className)}>
        <span className="font-sans font-medium text-ink-muted text-sm">
          Insufficient evidence
        </span>
        {showSubtitle && (
          <p className="text-xs text-ink-muted">
            Only baseline attributes could be observed
          </p>
        )}
      </div>
    );
  }

  const rounded = Math.round(score);

  return (
    <div className={cn('inline-flex flex-col', className)}>
      <div className="flex items-baseline gap-1">
        <span className="text-xs font-medium text-ink-muted">Risk score</span>
        <span
          className={cn(
            'font-display font-bold tracking-tight text-ink',
            size === 'lg' ? 'text-3xl' : size === 'sm' ? 'text-lg' : 'text-2xl'
          )}
        >
          {rounded}
        </span>
        <span className="text-xs font-mono text-ink-muted">/ 100</span>
      </div>
      {showSubtitle && (
        <span className="text-[11px] text-ink-muted italic">
          (not a probability)
        </span>
      )}
    </div>
  );
}
