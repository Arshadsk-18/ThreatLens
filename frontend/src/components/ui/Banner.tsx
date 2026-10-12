import React from 'react';
import { cn } from '@/lib/utils';
import { AlertCircle, Info, ShieldAlert } from 'lucide-react';

interface BannerProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'demo' | 'info' | 'warning' | 'error';
  message?: string;
  children?: React.ReactNode;
}

export function Banner({ variant = 'info', message, children, className, ...props }: BannerProps) {
  let icon = <Info className="h-4 w-4 shrink-0" aria-hidden="true" />;
  let style = 'bg-primary/10 text-primary border-primary/20';

  if (variant === 'demo') {
    icon = <ShieldAlert className="h-4 w-4 shrink-0 text-amber-400" aria-hidden="true" />;
    style = 'bg-amber-950/40 text-amber-200 border-amber-500/30 font-medium';
  } else if (variant === 'warning') {
    icon = <AlertCircle className="h-4 w-4 shrink-0 text-amber-400" aria-hidden="true" />;
    style = 'bg-amber-950/30 text-amber-200 border-amber-500/30';
  } else if (variant === 'error') {
    icon = <AlertCircle className="h-4 w-4 shrink-0 text-destructive" aria-hidden="true" />;
    style = 'bg-destructive/10 text-destructive border-destructive/20';
  }

  return (
    <div
      role="status"
      className={cn(
        'flex items-center gap-3 px-4 py-2.5 rounded-md border text-sm',
        style,
        className
      )}
      {...props}
    >
      {icon}
      <div className="flex-1">{message || children}</div>
    </div>
  );
}

export function DemoPersistentBanner({ className }: { className?: string }) {
  return (
    <Banner
      variant="demo"
      className={cn('w-full rounded-none border-x-0 border-t-0 border-b border-amber-500/30', className)}
    >
      <span className="font-semibold mr-1.5 uppercase tracking-wide text-xs bg-amber-500/20 px-2 py-0.5 rounded">
        Demo Mode Active
      </span>
      <span>Demo data. Simulated records are labelled.</span>
    </Banner>
  );
}
