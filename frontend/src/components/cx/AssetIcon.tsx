import React, { useState } from 'react';
import { cn } from '@/lib/utils';
import { Smartphone, Globe } from 'lucide-react';

export interface AssetIconProps {
  src?: string | null;
  alt: string;
  platform?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function AssetIcon({ src, alt, platform, size = 'md', className }: AssetIconProps) {
  const [hasError, setHasError] = useState(false);

  const sizeClasses =
    size === 'sm'
      ? 'w-7 h-7 rounded-[8px] text-xs'
      : size === 'lg'
      ? 'w-14 h-14 rounded-[14px] text-base'
      : 'w-10 h-10 rounded-[10px] text-sm';

  if (!src || hasError) {
    const initial = alt ? alt.trim().charAt(0).toUpperCase() : '?';

    return (
      <div
        className={cn(
          'flex items-center justify-center bg-surface-2 border border-hairline font-display font-bold text-ink shrink-0 select-none shadow-sm',
          sizeClasses,
          className
        )}
        aria-label={alt}
      >
        {platform === 'apple_app_store' ? (
          <Smartphone className="w-1/2 h-1/2 text-ink-muted" aria-hidden="true" />
        ) : platform === 'bluesky' ? (
          <Globe className="w-1/2 h-1/2 text-ink-muted" aria-hidden="true" />
        ) : (
          <span>{initial}</span>
        )}
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={alt}
      onError={() => setHasError(true)}
      className={cn(
        'object-cover border border-hairline bg-surface shrink-0 shadow-sm transition-transform',
        sizeClasses,
        className
      )}
      loading="lazy"
    />
  );
}
