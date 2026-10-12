import React from 'react';
import { Navigation } from './Navigation';
import { Shield, Moon, Sun, CircleDot } from 'lucide-react';
import { SourceBadge } from '@/components/cx/SourceBadge';

interface HeaderProps {
  currentBrandName?: string;
  isDemoBrand?: boolean;
  scanMode?: 'LIVE' | 'DEMO';
  onToggleScanMode?: () => void;
  isDark?: boolean;
  onToggleTheme?: () => void;
}

export function Header({
  currentBrandName = 'Kaveri Bank',
  isDemoBrand = true,
  scanMode = 'DEMO',
  onToggleScanMode,
  isDark = false,
  onToggleTheme,
}: HeaderProps) {
  return (
    <header className="border-b border-hairline bg-surface/80 backdrop-blur-md sticky top-0 z-40 transition-colors">
      <div className="container mx-auto px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-6">
          {/* Logo with calm Forensic Lens aesthetic */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-pill bg-ink text-surface dark:bg-surface dark:text-ink flex items-center justify-center font-display font-bold text-base shadow-sm">
              <Shield className="w-4 h-4 fill-current" aria-hidden="true" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-display font-bold text-lg tracking-tight text-ink">
                  ThreatLens
                </span>
                <span className="font-mono text-[10px] px-2 py-0.5 rounded-pill bg-surface-2 text-ink-muted border border-hairline">
                  v3.0.0
                </span>
              </div>
              <p className="text-[11px] text-ink-muted hidden sm:block">
                Forensic social & app look-alike intelligence
              </p>
            </div>
          </div>

          <div className="h-5 w-[1px] bg-hairline hidden md:block" />

          {/* Active Brand context pill */}
          <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-pill bg-surface-2 border border-hairline text-xs">
            <span className="text-ink-muted">Active brand:</span>
            <span className="font-medium text-ink">{currentBrandName}</span>
            {isDemoBrand && (
              <span className="text-[10px] font-mono px-2 py-0.2 rounded-pill bg-[#6D28D9]/10 text-[#6D28D9] dark:text-[#C4B5FD] border border-[#6D28D9]/30">
                Demo
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Scan mode pill button */}
          <div className="flex items-center gap-2">
            <button
              onClick={onToggleScanMode}
              type="button"
              className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lens rounded-pill transition-transform hover:scale-102"
              title="Toggle scan mode between DEMO and LIVE"
            >
              {scanMode === 'DEMO' ? (
                <SourceBadge status="SIMULATED" className="cursor-pointer" />
              ) : (
                <SourceBadge status="LIVE" className="cursor-pointer" />
              )}
            </button>
          </div>

          {/* Theme switcher pill button */}
          <button
            type="button"
            onClick={onToggleTheme}
            className="w-8 h-8 rounded-pill bg-surface-2 border border-hairline flex items-center justify-center text-ink-muted hover:text-ink transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lens"
            aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>

          <div className="hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-pill bg-surface-2 text-[11px] font-mono text-ink-muted border border-hairline">
            <CircleDot className="w-3 h-3 text-[#0E8F9C]" aria-hidden="true" />
            <span>/api/v1</span>
          </div>
        </div>
      </div>

      {/* Sub-header navigation bar */}
      <div className="border-t border-hairline bg-surface/50 px-6">
        <div className="container mx-auto">
          <Navigation />
        </div>
      </div>
    </header>
  );
}
