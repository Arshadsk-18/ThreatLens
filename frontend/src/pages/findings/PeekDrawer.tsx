import React from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import type { Schema } from "@/api/client";
import { ScoreBar } from "@/components/cx/ScoreBar";
import { SeverityPill } from "@/components/cx/SeverityPill";
import { SourceBadge } from "@/components/cx/SourceBadge";
import { StatusPill } from "@/components/cx/StatusPill";
import { AssetIcon } from "@/components/cx/AssetIcon";
import {
  X,
  ArrowRight,
  RotateCw,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface PeekDrawerProps {
  findingId: string | null;
  onClose: () => void;
  onOpenDecision: (finding: Schema["FindingListItem"]) => void;
}

export function PeekDrawer({ findingId, onClose, onOpenDecision }: PeekDrawerProps) {
  const { data: finding, isLoading } = useQuery({
    queryKey: ["finding", findingId],
    queryFn: () => (findingId ? apiClient.getFinding(findingId) : null),
    enabled: !!findingId,
  });

  const drawerRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!findingId) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
        return;
      }
      if (e.key === "Tab" && drawerRef.current) {
        const focusable = drawerRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];

        if (e.shiftKey) {
          if (document.activeElement === first || !drawerRef.current.contains(document.activeElement)) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (document.activeElement === last || !drawerRef.current.contains(document.activeElement)) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [findingId, onClose]);

  if (!findingId) return null;

  return (
    <div
      ref={drawerRef}
      role="dialog"
      aria-modal="true"
      aria-label="Signal Breakdown Peek"
      className="fixed inset-y-0 right-0 w-full sm:w-[480px] bg-surface border-l border-hairline shadow-2xl z-50 flex flex-col animate-in slide-from-right duration-200"
    >
      {/* Drawer Header */}
      <div className="p-4 border-b border-hairline flex items-center justify-between bg-surface-2/80">
        <div className="flex items-center gap-2">
          <span className="font-display font-semibold text-sm text-ink tracking-tight">
            Signal Breakdown Peek
          </span>
          <span className="font-mono text-[10px] text-ink-muted">({findingId})</span>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-lg text-ink-muted hover:text-ink hover:bg-surface transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lens"
          title="Close peek drawer"
          aria-label="Close peek drawer"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Drawer Body */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        {isLoading ? (
          <div className="py-20 text-center space-y-2">
            <RotateCw className="w-5 h-5 animate-spin text-lens mx-auto" />
            <span className="text-xs text-ink-muted">Loading candidate details...</span>
          </div>
        ) : finding ? (
          <>
            {/* Candidate Header Summary */}
            <div className="p-4 rounded-panel-nested bg-surface-2 border border-hairline space-y-3">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <AssetIcon
                    src={finding.candidate.icon_url || undefined}
                    alt={finding.candidate.display_name}
                    size="md"
                  />
                  <div>
                    <h3 className="font-display font-bold text-sm text-ink leading-snug">
                      {finding.candidate.display_name}
                    </h3>
                    <span className="font-mono text-[11px] text-ink-muted block">
                      {finding.candidate.platform} · {finding.candidate.stable_identifier}
                    </span>
                  </div>
                </div>
                <SeverityPill severity={finding.severity} />
              </div>

              <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-hairline/60">
                <SourceBadge status={finding.source_mode} />
                <StatusPill status={finding.status} />
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-pill bg-surface text-ink border border-hairline">
                  Technique: {finding.technique}
                </span>
                <span className="text-[10px] font-mono text-ink-muted ml-auto">
                  Risk score: <strong className="text-ink">{finding.risk_score}/100</strong>
                </span>
              </div>
            </div>

            {/* Top Signals */}
            <div className="space-y-2">
              <span className="text-xs font-semibold text-ink uppercase tracking-wider block">
                Top Fired Signals
              </span>
              <div className="space-y-2">
                {finding.top_signals.map((sig) => (
                  <div
                    key={sig.signal}
                    className="p-3 rounded-panel-nested border border-hairline bg-surface-2 space-y-1.5"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-mono font-semibold text-ink">{sig.signal}</span>
                      <span className="font-mono text-ink font-bold">
                        +{sig.points} / {sig.max_points} pts
                      </span>
                    </div>
                    <ScoreBar value={sig.points} max={sig.max_points} />
                    <p className="text-[11px] text-ink-muted leading-relaxed">{sig.reason}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* IdentityGuard Status */}
            <div className="p-3.5 rounded-panel-nested bg-surface-2 border border-hairline space-y-1.5">
              <div className="flex items-center justify-between text-xs font-semibold">
                <span className="text-ink">IdentityGuard Status</span>
                <span className="font-mono text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200 text-[10px]">
                  {finding.identity_guard.decision}
                </span>
              </div>
              <p className="text-[11px] text-ink-muted leading-relaxed">
                {finding.identity_guard.explanation}
              </p>
            </div>

            {/* Score Breakdown List */}
            {finding.score_breakdown && (
              <div className="space-y-2">
                <span className="text-xs font-semibold text-ink uppercase tracking-wider block">
                  All Observable Signals ({finding.score_breakdown.length})
                </span>
                <div className="space-y-2">
                  {finding.score_breakdown.map((sb) => (
                    <div
                      key={sb.signal}
                      className={cn(
                        "p-3 rounded-panel-nested border text-xs space-y-1",
                        sb.status === "UNAVAILABLE"
                          ? "bg-surface-2/40 border-hairline/60 opacity-60"
                          : "bg-surface-2 border-hairline"
                      )}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-medium text-ink">{sb.signal}</span>
                        <div className="flex items-center gap-2">
                          <span
                            className={cn(
                              "text-[9px] font-mono px-1.5 py-0.2 rounded font-semibold",
                              sb.status === "OBSERVED"
                                ? "bg-emerald-50 text-emerald-800"
                                : sb.status === "UNAVAILABLE"
                                ? "bg-surface text-ink-muted border border-hairline"
                                : "bg-lens/10 text-lens"
                            )}
                          >
                            {sb.status}
                          </span>
                          <span className="font-mono font-bold text-ink">
                            {sb.points} / {sb.max_points}
                          </span>
                        </div>
                      </div>
                      <p className="text-[11px] text-ink-muted">{sb.reason}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : null}
      </div>

      {/* Drawer Footer Actions */}
      {finding && (
        <div className="p-4 border-t border-hairline bg-surface-2 flex items-center justify-between gap-3">
          <button
            onClick={() => {
              onClose();
              onOpenDecision(finding);
            }}
            className="px-3.5 py-1.5 text-xs font-semibold text-ink hover:bg-surface border border-hairline rounded-pill transition-colors"
          >
            Record Decision
          </button>
          <Link
            to={`/findings/${finding.id}`}
            className="px-4 py-1.5 text-xs font-semibold text-white bg-ink rounded-pill hover:bg-ink/90 flex items-center gap-1.5 transition-colors"
          >
            <span>Evidence Compare</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}
    </div>
  );
}
