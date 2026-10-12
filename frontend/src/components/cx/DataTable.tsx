import * as React from 'react';
import { cn } from '@/lib/utils';

export function DataTable({ className, ...props }: React.HTMLAttributes<HTMLTableElement>) {
  return (
    <div className="w-full overflow-x-auto rounded-nested border border-hairline bg-surface">
      <table className={cn('w-full text-left text-sm border-collapse', className)} {...props} />
    </div>
  );
}

export function DataTableHeader({ className, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <thead
      className={cn('bg-surface-2 border-b border-hairline text-xs font-semibold text-ink-muted', className)}
      {...props}
    />
  );
}

export function DataTableBody({ className, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody className={cn('divide-y divide-hairline', className)} {...props} />;
}

export function DataTableRow({
  className,
  onClick,
  ...props
}: React.HTMLAttributes<HTMLTableRowElement>) {
  const isClickable = Boolean(onClick);

  return (
    <tr
      tabIndex={isClickable ? 0 : undefined}
      onClick={onClick}
      onKeyDown={(e) => {
        if (isClickable && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          onClick?.(e as unknown as React.MouseEvent<HTMLTableRowElement>);
        }
      }}
      className={cn(
        'transition-colors',
        isClickable &&
          'cursor-pointer hover:bg-surface-2 focus-visible:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lens focus-visible:ring-inset',
        className
      )}
      {...props}
    />
  );
}

export function DataTableHead({ className, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      scope="col"
      className={cn('py-3 px-4 font-medium text-ink-muted text-xs whitespace-nowrap', className)}
      {...props}
    />
  );
}

export function DataTableCell({ className, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={cn('py-3.5 px-4 text-ink text-sm align-middle', className)} {...props} />;
}
