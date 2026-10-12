import React from 'react';
import { cn } from '@/lib/utils';

export interface ScoreBarProps {
  points?: number;
  maxPoints?: number;
  value?: number;
  max?: number;
  label?: string;
  className?: string;
}

export function ScoreBar({
  points: pointsProp,
  maxPoints: maxPointsProp,
  value,
  max,
  label,
  className,
}: ScoreBarProps) {
  const points = pointsProp !== undefined ? pointsProp : value !== undefined ? value : 0;
  const maxPoints = maxPointsProp !== undefined ? maxPointsProp : max !== undefined ? max : 100;
  const percent = maxPoints > 0 ? Math.min(100, Math.max(0, (points / maxPoints) * 100)) : 0;

  return (
    <div className={cn('w-full space-y-1', className)}>
      {(label || pointsProp !== undefined || maxPointsProp !== undefined) && (
        <div className="flex items-center justify-between text-xs">
          {label && <span className="font-medium text-ink-muted">{label}</span>}
          <span className="font-mono text-ink font-semibold ml-auto">
            {Number(points.toFixed(1))} / {maxPoints} pts
          </span>
        </div>
      )}
      <div className="h-1.5 w-full bg-hairline rounded-pill overflow-hidden">
        <div
          className={cn(
            'h-full rounded-pill transition-all duration-300',
            percent >= 75 ? 'bg-severity-high' : percent >= 40 ? 'bg-severity-medium' : 'bg-lens'
          )}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
