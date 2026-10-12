import React from 'react';
import { cn } from '@/lib/utils';

export interface CoverageMeterProps {
  coverage: number; // 0.0 to 1.0
  className?: string;
}

export function CoverageMeter({ coverage, className }: CoverageMeterProps) {
  const percent = Math.min(100, Math.max(0, Math.round(coverage * 100)));
  const isSufficient = coverage >= 0.5;

  return (
    <div className={cn('space-y-1', className)}>
      <div className="flex items-center justify-between text-xs">
        <span className="text-ink-muted">Evidence coverage</span>
        <span className="font-mono font-semibold text-ink">{percent}%</span>
      </div>
      <div className="h-1.5 w-full bg-hairline rounded-pill overflow-hidden">
        <div
          className={cn(
            'h-full rounded-pill transition-all duration-300',
            isSufficient ? 'bg-[#0E8F9C]' : 'bg-[#B7791F]'
          )}
          style={{ width: `${percent}%` }}
        />
      </div>
      {!isSufficient && (
        <p className="text-[11px] text-[#B7791F] dark:text-[#F6E05E]">
          Insufficient evidence: coverage under 50% triggers G3 cap (max Medium).
        </p>
      )}
    </div>
  );
}
