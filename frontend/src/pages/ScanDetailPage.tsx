import React, { useState, useEffect, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import { ApiError } from "@/api/errors";
import { SCAN_ID } from "@/api/mock-data/fixtures";
import type { Schema } from "@/api/client";
import { SourceBadge } from "@/components/cx/SourceBadge";
import { FunnelBars } from "@/components/cx/FunnelBars";
import {
  RotateCw,
  AlertTriangle,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  Shield,
  Terminal,
} from "lucide-react";
import { cn } from "@/lib/utils";

const PIPELINE_STAGES: Array<{
  key: Schema["ScanStage"];
  label: string;
  nominalProgress: number;
}> = [
  { key: "queued", label: "Queued", nominalProgress: 0 },
  { key: "resolving_brand", label: "Resolve Brand", nominalProgress: 5 },
  { key: "planning_queries", label: "Plan Queries", nominalProgress: 10 },
  { key: "fetching", label: "Fetch Sources", nominalProgress: 35 },
  { key: "normalizing", label: "Normalize & Dedupe", nominalProgress: 60 },
  { key: "hashing_images", label: "Hash Icons", nominalProgress: 70 },
  { key: "assessing", label: "Score & IdentityGuard", nominalProgress: 85 },
  { key: "persisting", label: "Persist", nominalProgress: 98 },
  { key: "completed", label: "Completed", nominalProgress: 100 },
];

export function ScanDetailPage() {
  const { id } = useParams<{ id: string }>();
  const scanId = id || SCAN_ID;

  // Event feed auto-scroll toggle (OFF by default per rubric)
  const [autoScroll, setAutoScroll] = useState(false);
  const eventLogRef = useRef<HTMLDivElement>(null);

  const { data: scan, isLoading, isError, error } = useQuery({
    queryKey: ["scan-detail", scanId],
    queryFn: () => apiClient.getScan(scanId),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 1000;
      // Poll every 1 s while QUEUED or RUNNING, stop on terminal status
      return data.status === "QUEUED" || data.status === "RUNNING" ? 1000 : false;
    },
  });

  // Handle auto-scroll if enabled
  useEffect(() => {
    if (autoScroll && eventLogRef.current) {
      eventLogRef.current.scrollTop = eventLogRef.current.scrollHeight;
    }
  }, [scan?.events, autoScroll]);

  if (isLoading) {
    return (
      <div className="p-12 text-center space-y-3 animate-fade-in">
        <RotateCw className="w-6 h-6 animate-spin text-lens mx-auto" />
        <p className="text-xs text-ink-muted">Connecting to scan execution pipeline {scanId}...</p>
      </div>
    );
  }

  if (isError || !scan) {
    return (
      <div className="p-8 rounded-panel border border-risk-critical/30 bg-risk-critical/5 text-risk-critical text-xs space-y-3 max-w-lg mx-auto">
        <div className="flex items-center gap-2 font-semibold">
          <AlertCircle className="w-5 h-5" />
          <span>Scan Not Found or Inaccessible</span>
        </div>
        <p className="text-ink-muted">
          {error instanceof ApiError ? error.message : `Could not retrieve scan records for identifier ${scanId}.`}
        </p>
        {error instanceof ApiError && error.requestId && (
          <span className="font-mono text-[10px] text-ink-muted block">
            Request ID: {error.requestId}
          </span>
        )}
        <Link
          to="/scan"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-pill bg-ink text-white font-semibold text-xs"
        >
          <ArrowRight className="w-3.5 h-3.5 rotate-180" />
          <span>Return to Scan Setup</span>
        </Link>
      </div>
    );
  }

  const isTerminal =
    scan.status === "COMPLETED" ||
    scan.status === "COMPLETED_WITH_ERRORS" ||
    scan.status === "FAILED";

  // Compute failed sources for COMPLETED_WITH_ERRORS banner
  const failedSources = scan.source_outcomes.filter(
    (s) => s.status === "RATE_LIMITED" || s.status === "ERROR" || s.status === "PARTIAL"
  );

  // Compute sources counts for honest empty copy
  const queriedSources = scan.source_outcomes.filter((s) => s.status !== "NOT_CONNECTED");
  const notConnectedSources = scan.source_outcomes.filter((s) => s.status === "NOT_CONNECTED");
  const findingsTotal = scan.funnel.findings;

  // Active stage index
  const activeStageIndex = PIPELINE_STAGES.findIndex((s) => s.key === scan.stage);

  return (
    <div className="space-y-8 animate-fade-in pb-16">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-hairline">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="font-display font-bold text-2xl text-ink tracking-tight">
              Scan Detail
            </h1>
            <span className="font-mono text-sm text-ink-muted">({scan.id})</span>
            <SourceBadge status={scan.mode === "DEMO" ? "SIMULATED" : "LIVE"} />
            <SourceBadge status={scan.status} />
          </div>
          <p className="text-xs text-ink-muted mt-1">
            Target Brand: <code className="font-mono text-ink font-semibold">{scan.brand_id}</code> ·
            Initiated at {new Date(scan.created_at).toLocaleTimeString()}
            {scan.completed_at && ` · Completed at ${new Date(scan.completed_at).toLocaleTimeString()}`}
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <Link
            to="/scan"
            className="px-3.5 py-1.5 text-xs font-semibold text-ink-muted hover:text-ink bg-surface border border-hairline rounded-pill hover:bg-hairline/60 transition-colors"
          >
            New Scan
          </Link>
          {findingsTotal > 0 && (
            <Link
              to={`/findings?scan_id=${scan.id}`}
              className="px-4 py-1.5 text-xs font-semibold text-white bg-ink rounded-pill shadow-sm hover:bg-ink/90 flex items-center gap-1.5 transition-colors"
            >
              <span>Review Findings ({findingsTotal})</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          )}
        </div>
      </div>

      {/* COMPLETED_WITH_ERRORS Status Banner */}
      {scan.status === "COMPLETED_WITH_ERRORS" && failedSources.length > 0 && (
        <div className="p-4 rounded-panel border border-amber-300 bg-amber-50 text-amber-900 text-xs space-y-1.5">
          <div className="flex items-center gap-2 font-semibold">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
            <span>Scan completed with partial coverage</span>
          </div>
          <p className="text-[11px] leading-relaxed">
            The following source(s) encountered rate limits or connection failures:{" "}
            <strong>
              {failedSources
                .map((fs) => `${fs.source_id} (${fs.status})`)
                .join(", ")}
            </strong>
            . Partial candidate results retrieved prior to failure were preserved in accordance with contract section 5.3.
          </p>
        </div>
      )}

      {/* Section 5.2 Stage Tracker & Pipeline Progress */}
      <div className="rounded-panel border border-hairline bg-surface p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-hairline">
          <div>
            <h2 className="font-display font-semibold text-sm text-ink tracking-tight">
              Pipeline Stage & Execution Progress
            </h2>
            <p className="text-xs text-ink-muted">
              Section 5.2 sequential stages: query planning, parallel fetching, deduplication, perceptual hashing, and scoring.
            </p>
          </div>
          <div className="text-right">
            <span className="font-mono text-base font-bold text-lens">
              {scan.progress_percent}%
            </span>
            <span className="text-[10px] text-ink-muted block uppercase tracking-wider font-mono">
              {scan.stage}
            </span>
          </div>
        </div>

        {/* Linear Progress Bar */}
        <div className="h-2 w-full bg-surface-2 rounded-pill overflow-hidden border border-hairline/60">
          <div
            className={cn(
              "h-full rounded-pill transition-all duration-500",
              scan.status === "FAILED"
                ? "bg-risk-critical"
                : scan.status === "COMPLETED_WITH_ERRORS"
                ? "bg-amber-500"
                : "bg-lens"
            )}
            style={{ width: `${Math.max(scan.progress_percent, 2)}%` }}
          />
        </div>

        {/* Sequential Stepper */}
        <div className="grid grid-cols-3 sm:grid-cols-5 md:grid-cols-9 gap-1.5 pt-2">
          {PIPELINE_STAGES.map((st, idx) => {
            const isPassed =
              scan.status === "COMPLETED" ||
              scan.status === "COMPLETED_WITH_ERRORS" ||
              idx < activeStageIndex;
            const isCurrent = idx === activeStageIndex && !isTerminal;

            return (
              <div
                key={st.key}
                className={cn(
                  "p-2 rounded-panel-nested border text-center transition-colors space-y-1",
                  isCurrent
                    ? "bg-lens/10 border-lens text-lens shadow-xs ring-1 ring-lens/30"
                    : isPassed
                    ? "bg-surface-2 border-hairline text-ink opacity-90"
                    : "bg-surface-2/40 border-hairline/40 text-ink-muted opacity-40"
                )}
              >
                <div className="flex items-center justify-center">
                  {isCurrent ? (
                    <RotateCw className="w-3 h-3 animate-spin text-lens" />
                  ) : isPassed ? (
                    <CheckCircle2 className="w-3 h-3 text-[#0E8F9C]" />
                  ) : (
                    <span className="w-2 h-2 rounded-full bg-hairline" />
                  )}
                </div>
                <span className="block text-[10px] font-medium leading-tight truncate" title={st.label}>
                  {st.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Funnel Visual */}
      <FunnelBars funnel={scan.funnel} scanId={scan.id} />

      {/* Empty Findings Notice (computed honestly per 15.3 copy rule) */}
      {isTerminal && findingsTotal === 0 && (
        <div className="rounded-panel border border-hairline bg-surface p-6 shadow-sm text-center space-y-2">
          <Shield className="w-8 h-8 text-[#0E8F9C] mx-auto" />
          <h3 className="font-display font-semibold text-sm text-ink">
            No candidates for review in this scan. {queriedSources.length} sources were queried, {notConnectedSources.length} was not connected.
          </h3>
          <p className="text-xs text-ink-muted max-w-md mx-auto">
            All candidate records returned by active providers were cleared by IdentityGuard (exact app/developer ID match) or evaluated as benign namesakes.
          </p>
          <div className="pt-2">
            <Link
              to={`/cleared?scan_id=${scan.id}`}
              className="inline-flex items-center gap-1.5 text-xs text-lens font-semibold hover:underline"
            >
              <span>Inspect Cleared Entities ({scan.funnel.official_cleared})</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      )}

      {/* Per-Source Outcome Cards */}
      <div className="rounded-panel border border-hairline bg-surface p-6 shadow-sm space-y-4">
        <div className="pb-3 border-b border-hairline">
          <h2 className="font-display font-semibold text-base text-ink tracking-tight">
            Per-Source Query Outcomes
          </h2>
          <p className="text-xs text-ink-muted mt-0.5">
            Transparent query execution records, rate limit counters, cache hits, and provider status indicators.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
          {scan.source_outcomes.map((outcome) => {
            const isNotConnected = outcome.status === "NOT_CONNECTED";
            const isFailure =
              outcome.status === "RATE_LIMITED" ||
              outcome.status === "ERROR" ||
              outcome.status === "PARTIAL";

            // Format cache time per rubric §15.3: "Cached result from 05:12 UTC"
            const cacheTimeStr =
              outcome.source_mode === "CACHED" && outcome.retrieved_at
                ? `Cached result from ${new Date(outcome.retrieved_at).toISOString().substring(11, 16)} UTC`
                : null;

            return (
              <div
                key={outcome.source_id}
                className={cn(
                  "p-4 rounded-panel-nested border text-xs flex flex-col justify-between space-y-3 transition-colors",
                  isNotConnected
                    ? "bg-surface-2/60 border-hairline/80 text-ink-muted"
                    : isFailure
                    ? "bg-amber-500/5 border-amber-300 text-ink"
                    : "bg-surface-2 border-hairline text-ink"
                )}
              >
                {/* Header */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono font-bold text-xs text-ink block truncate" title={outcome.source_id}>
                      {outcome.source_id}
                    </span>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <SourceBadge status={outcome.status} />
                      {outcome.source_mode && (
                        <SourceBadge status={outcome.source_mode} />
                      )}
                    </div>
                  </div>

                  {cacheTimeStr && (
                    <span className="text-[10px] font-mono text-lens block">
                      {cacheTimeStr}
                    </span>
                  )}
                </div>

                {/* Outcome Message (Strict 15.3 Copy) */}
                <div className="text-[11px] leading-relaxed">
                  {isNotConnected ? (
                    <span className="text-ink-muted">
                      <strong className="text-ink">{outcome.source_id}:</strong> not connected. {outcome.message || "Requires platform API access."} Not queried.
                    </span>
                  ) : isFailure ? (
                    <span className="text-amber-900 font-medium">
                      <strong className="text-ink">{outcome.source_id}:</strong> {outcome.message || "Encountered provider failure; partial results preserved."}
                    </span>
                  ) : (
                    <span className="text-ink-muted">
                      {outcome.message}
                    </span>
                  )}
                </div>

                {/* Metrics Breakdown */}
                {!isNotConnected && (
                  <div className="pt-2 border-t border-hairline/60 grid grid-cols-2 gap-2 text-[10px] font-mono text-ink-muted">
                    <div>
                      <span>Queries: </span>
                      <strong className="text-ink">
                        {outcome.queries_executed} / {outcome.queries_planned}
                      </strong>
                    </div>
                    <div>
                      <span>Candidates: </span>
                      <strong className="text-ink">
                        {outcome.candidate_count}
                      </strong>
                    </div>
                    <div>
                      <span>Cache hits: </span>
                      <strong className="text-ink">
                        {outcome.cache_hit_count}
                      </strong>
                    </div>
                    <div>
                      <span>Duration: </span>
                      <strong className="text-ink">
                        {outcome.duration_ms} ms
                      </strong>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Event Log Feed */}
      <div className="rounded-panel border border-hairline bg-surface p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-hairline">
          <div className="flex items-center gap-2">
            <Terminal className="w-4 h-4 text-lens" />
            <div>
              <h2 className="font-display font-semibold text-base text-ink tracking-tight">
                Live Pipeline Event Feed
              </h2>
              <p className="text-xs text-ink-muted">
                Audit stream recording stage transitions, query dispatches, and IdentityGuard decisions.
              </p>
            </div>
          </div>

          {/* Auto-scroll toggle (OFF by default) */}
          <label className="flex items-center gap-2 text-xs text-ink-muted cursor-pointer">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="w-3.5 h-3.5 rounded text-lens"
            />
            <span>Auto-scroll feed</span>
          </label>
        </div>

        {/* Feed Container */}
        <div
          ref={eventLogRef}
          className="max-h-72 overflow-y-auto bg-surface-2 p-3.5 rounded-panel-nested border border-hairline font-mono text-xs space-y-2"
        >
          {scan.events.length === 0 ? (
            <div className="text-center py-6 text-ink-muted text-[11px]">
              No events recorded yet.
            </div>
          ) : (
            scan.events.slice(-50).map((ev, index) => {
              const timeStr = new Date(ev.at).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              });

              return (
                <div
                  key={index}
                  className="flex items-start gap-2.5 text-[11px] leading-snug py-0.5 hover:bg-surface/50 rounded px-1 transition-colors"
                >
                  <span className="text-ink-muted shrink-0">{timeStr}</span>

                  <span
                    className={cn(
                      "px-1.5 py-0.2 rounded text-[9px] font-bold uppercase shrink-0",
                      ev.level === "ERROR"
                        ? "bg-risk-critical/10 text-risk-critical"
                        : ev.level === "WARNING"
                        ? "bg-amber-100 text-amber-800"
                        : "bg-lens/10 text-lens"
                    )}
                  >
                    {ev.level}
                  </span>

                  {ev.source_id && (
                    <span className="text-ink font-semibold shrink-0">
                      [{ev.source_id}]
                    </span>
                  )}

                  <span className="text-ink-muted break-all">
                    {ev.message}
                  </span>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
