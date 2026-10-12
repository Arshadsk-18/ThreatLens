import React from 'react';

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  width?: string | number;
  height?: string | number;
  borderRadius?: string | number;
}

export function Skeleton({
  width,
  height,
  borderRadius = '6px',
  style,
  className = '',
  ...props
}: SkeletonProps) {
  return (
    <div
      role="status"
      aria-label="Loading..."
      className={`threatlens-skeleton ${className}`}
      style={{
        width,
        height,
        borderRadius,
        backgroundColor: 'var(--border-subtle, rgba(255, 255, 255, 0.08))',
        animation: 'pulse 1.8s ease-in-out infinite',
        ...style,
      }}
      {...props}
    />
  );
}
