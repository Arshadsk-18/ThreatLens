import React from 'react';
import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { CheckCircle2, ArrowUpRight } from 'lucide-react';

export interface FunnelData {
  retrieved: number;
  deduplicated: number;
  official_cleared: number;
  not_relevant: number;
  benign_lookalike: number;
  below_threshold: number;
  findings: number;
}

export interface FunnelBarsProps {
  funnel: FunnelData;
  scanId?: string;
  className?: string;
}

export function FunnelBars({ funnel, scanId, className }: FunnelBarsProps) {
  const sumOfParts =
    funnel.official_cleared +
    funnel.not_relevant +
    funnel.benign_lookalike +
    funnel.below_threshold +
    funnel.findings;
  const invariantSatisfied = funnel.deduplicated === sumOfParts;

  const maxVal = Math.max(funnel.retrieved, 1);

  return (
    <div className={cn('rounded-panel border border-hairline bg-surface p-6 space-y-5', className)}>
      <div className="flex items-center justify-between pb-2 border-b border-hairline">
        <div>
          <h3 className="font-display font-semibold text-base text-ink">
            Detection & Filtering Funnel
          </h3>
          <p className="text-xs text-ink-muted">
            Entity deduplication and multi-gate filtering
          </p>
        </div>
        <div
          className={cn(
            'inline-flex items-center gap-1.5 px-3 py-1 rounded-pill text-xs font-medium',
            invariantSatisfied
              ? 'bg-[#0E8F9C]/10 text-[#0E8F9C] border border-[#0E8F9C]/30'
              : 'bg-[#A4123F]/10 text-[#A4123F] border border-[#A4123F]/30'
          )}
        >
          <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" />
          <span>
            {invariantSatisfied
              ? 'Invariant satisfied: 100% accounted for'
              : 'Invariant mismatch detected'}
          </span>
        </div>
      </div>

      {/* Top 2 Raw Volumes */}
      <div className="space-y-3">
        <div className="space-y-1">
          <div className="flex justify-between text-xs">
            <span className="font-medium text-ink">Raw records retrieved</span>
            <span className="font-mono font-bold text-ink">{funnel.retrieved}</span>
          </div>
          <div className="h-2 w-full bg-surface-2 rounded-pill overflow-hidden">
            <div
              className="h-full bg-ink rounded-pill transition-all"
              style={{ width: `${(funnel.retrieved / maxVal) * 100}%` }}
            />
          </div>
        </div>

        <div className="space-y-1">
          <div className="flex justify-between text-xs">
            <span className="font-medium text-ink">Deduplicated unique entities</span>
            <span className="font-mono font-bold text-ink">{funnel.deduplicated}</span>
          </div>
          <div className="h-2 w-full bg-surface-2 rounded-pill overflow-hidden">
            <div
              className="h-full bg-lens rounded-pill transition-all"
              style={{ width: `${(funnel.deduplicated / maxVal) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Segmented Outcome Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 pt-2">
        {scanId ? (
          <Link
            to={`/cleared?scan_id=${scanId}`}
            className="p-3 rounded-nested bg-surface-2 border border-hairline text-center space-y-1 hover:border-lens transition-colors group block relative"
            title="View cleared records for this scan"
          >
            <div className="flex items-center justify-center gap-1">
              <span className="text-[11px] text-ink-muted group-hover:text-lens transition-colors">Official cleared</span>
              <ArrowUpRight className="w-3 h-3 text-ink-muted group-hover:text-lens" />
            </div>
            <span className="font-display font-bold text-lg text-[#0E8F9C] block">
              {funnel.official_cleared}
            </span>
            <span className="text-[10px] text-ink-muted font-mono block">Exact ID / Dev</span>
          </Link>
        ) : (
          <div className="p-3 rounded-nested bg-surface-2 border border-hairline text-center space-y-1">
            <span className="text-[11px] text-ink-muted block">Official cleared</span>
            <span className="font-display font-bold text-lg text-[#0E8F9C] block">
              {funnel.official_cleared}
            </span>
            <span className="text-[10px] text-ink-muted font-mono block">Exact ID / Dev</span>
          </div>
        )}

        <div className="p-3 rounded-nested bg-surface-2 border border-hairline text-center space-y-1">
          <span className="text-[11px] text-ink-muted block">Not relevant</span>
          <span className="font-display font-bold text-lg text-ink-muted block">
            {funnel.not_relevant}
          </span>
          <span className="text-[10px] text-ink-muted font-mono block">G1 (&lt; 0.60)</span>
        </div>

        <div className="p-3 rounded-nested bg-surface-2 border border-hairline text-center space-y-1">
          <span className="text-[11px] text-ink-muted block">Benign lookalike</span>
          <span className="font-display font-bold text-lg text-[#55627F] dark:text-[#A0AEC0] block">
            {funnel.benign_lookalike}
          </span>
          <span className="text-[10px] text-ink-muted font-mono block">G4 & G5 gates</span>
        </div>

        <div className="p-3 rounded-nested bg-surface-2 border border-hairline text-center space-y-1">
          <span className="text-[11px] text-ink-muted block">Below threshold</span>
          <span className="font-display font-bold text-lg text-ink-muted block">
            {funnel.below_threshold}
          </span>
          <span className="text-[10px] text-ink-muted font-mono block">&lt; 25 score pts</span>
        </div>

        {scanId ? (
          <Link
            to={`/findings?scan_id=${scanId}`}
            className="p-3 rounded-nested bg-severity-high/10 border border-severity-high/30 text-center space-y-1 hover:border-severity-high transition-colors group block relative"
            title="View findings for this scan"
          >
            <div className="flex items-center justify-center gap-1">
              <span className="text-[11px] text-severity-high font-semibold">Findings</span>
              <ArrowUpRight className="w-3 h-3 text-severity-high" />
            </div>
            <span className="font-display font-bold text-lg text-severity-high block">
              {funnel.findings}
            </span>
            <span className="text-[10px] text-severity-high/80 font-mono block">Review queue</span>
          </Link>
        ) : (
          <div className="p-3 rounded-nested bg-severity-high/10 border border-severity-high/30 text-center space-y-1">
            <span className="text-[11px] text-severity-high font-semibold block">Findings</span>
            <span className="font-display font-bold text-lg text-severity-high block">
              {funnel.findings}
            </span>
            <span className="text-[10px] text-severity-high/80 font-mono block">Review queue</span>
          </div>
        )}
      </div>

      <div className="text-[11px] text-ink-muted text-center pt-1 font-mono bg-surface-2/60 p-2 rounded-panel-nested border border-hairline">
        Invariant note: {funnel.deduplicated} (deduplicated) = {funnel.official_cleared} (cleared) + {funnel.not_relevant} (not relevant) + {funnel.benign_lookalike} (benign lookalike) + {funnel.below_threshold} (below threshold) + {funnel.findings} (findings).
      </div>
    </div>
  );
}
