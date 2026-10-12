import React from 'react';
import { cn } from '@/lib/utils';
import { FlaskConical } from 'lucide-react';

export interface DemoBannerProps {
  className?: string;
}

export function DemoBanner({ className }: DemoBannerProps) {
  return (
    <div
      role="status"
      className={cn(
        'w-full bg-ink text-surface dark:bg-surface dark:text-ink px-4 py-2 border-b border-hairline flex items-center justify-center gap-2 text-xs font-medium',
        className
      )}
    >
      <FlaskConical className="w-3.5 h-3.5 text-[#C4B5FD] shrink-0" aria-hidden="true" />
      <span>Demo data. Simulated records are labelled.</span>
    </div>
  );
}
