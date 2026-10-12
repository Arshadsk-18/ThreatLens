import React from 'react';
import { cn } from '@/lib/utils';
import { AlertTriangle, Loader2, Inbox, Unplug } from 'lucide-react';
import { Button } from './Button';

export interface LoadingStateProps {
  message?: string;
  className?: string;
}

export function LoadingState({ message = 'Loading monitoring data...', className }: LoadingStateProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn('flex flex-col items-center justify-center p-12 text-center space-y-3', className)}
    >
      <Loader2 className="h-8 w-8 animate-spin text-primary" aria-hidden="true" />
      <p className="text-sm text-muted-foreground">{message}</p>
    </div>
  );
}

export interface EmptyStateProps {
  title?: string;
  description: string;
  actionText?: string;
  onAction?: () => void;
  className?: string;
}

export function EmptyState({
  title = 'No records found',
  description,
  actionText,
  onAction,
  className,
}: EmptyStateProps) {
  return (
    <div
      role="status"
      className={cn(
        'flex flex-col items-center justify-center p-12 text-center space-y-3 rounded-lg border border-dashed border-border bg-card/30',
        className
      )}
    >
      <div className="p-3 rounded-full bg-muted/50 text-muted-foreground">
        <Inbox className="h-6 w-6" aria-hidden="true" />
      </div>
      <h4 className="text-base font-semibold text-foreground">{title}</h4>
      <p className="text-sm text-muted-foreground max-w-md leading-relaxed">{description}</p>
      {actionText && onAction && (
        <Button variant="outline" size="sm" onClick={onAction} className="mt-2">
          {actionText}
        </Button>
      )}
    </div>
  );
}

export interface ErrorStateProps {
  title?: string;
  message: string;
  requestId?: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({
  title = 'Unable to load data',
  message,
  requestId,
  onRetry,
  className,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        'flex flex-col items-center justify-center p-12 text-center space-y-3 rounded-lg border border-destructive/30 bg-destructive/5',
        className
      )}
    >
      <div className="p-3 rounded-full bg-destructive/10 text-destructive">
        <AlertTriangle className="h-6 w-6" aria-hidden="true" />
      </div>
      <h4 className="text-base font-semibold text-foreground">{title}</h4>
      <p className="text-sm text-muted-foreground max-w-md">{message}</p>
      {requestId && (
        <p className="text-xs font-mono text-muted-foreground">Request ID: {requestId}</p>
      )}
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry} className="mt-2">
          Retry request
        </Button>
      )}
    </div>
  );
}

export interface NotConnectedStateProps {
  platformName: string;
  reason?: string;
  className?: string;
}

export function NotConnectedState({
  platformName,
  reason = 'Requires platform API access or credentials. Not queried.',
  className,
}: NotConnectedStateProps) {
  return (
    <div
      role="status"
      className={cn(
        'flex flex-col items-center justify-center p-8 text-center space-y-3 rounded-lg border border-zinc-700/50 bg-zinc-900/40',
        className
      )}
    >
      <div className="p-3 rounded-full bg-zinc-800 text-zinc-400">
        <Unplug className="h-5 w-5" aria-hidden="true" />
      </div>
      <div className="space-y-1">
        <h4 className="text-sm font-semibold text-zinc-200">
          {platformName}: not connected
        </h4>
        <p className="text-xs text-zinc-400 max-w-md leading-relaxed">{reason}</p>
      </div>
      <span className="inline-flex items-center text-xs font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 border border-zinc-700">
        Status: NOT_CONNECTED
      </span>
    </div>
  );
}

export interface StateContainerProps {
  isLoading?: boolean;
  loadingMessage?: string;
  isError?: boolean;
  errorMessage?: string;
  requestId?: string;
  onRetry?: () => void;
  isNotConnected?: boolean;
  notConnectedPlatform?: string;
  notConnectedReason?: string;
  isEmpty?: boolean;
  emptyTitle?: string;
  emptyMessage?: string;
  onEmptyAction?: () => void;
  emptyActionText?: string;
  children: React.ReactNode;
}

export function StateContainer({
  isLoading,
  loadingMessage,
  isError,
  errorMessage,
  requestId,
  onRetry,
  isNotConnected,
  notConnectedPlatform,
  notConnectedReason,
  isEmpty,
  emptyTitle,
  emptyMessage,
  onEmptyAction,
  emptyActionText,
  children,
}: StateContainerProps) {
  if (isLoading) {
    return <LoadingState message={loadingMessage} />;
  }
  if (isError) {
    return (
      <ErrorState
        message={errorMessage || 'An unexpected error occurred while loading data.'}
        requestId={requestId}
        onRetry={onRetry}
      />
    );
  }
  if (isNotConnected && notConnectedPlatform) {
    return <NotConnectedState platformName={notConnectedPlatform} reason={notConnectedReason} />;
  }
  if (isEmpty && emptyMessage) {
    return (
      <EmptyState
        title={emptyTitle}
        description={emptyMessage}
        onAction={onEmptyAction}
        actionText={emptyActionText}
      />
    );
  }
  return <>{children}</>;
}
