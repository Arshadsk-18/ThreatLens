import React from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import { ApiError } from "@/api/errors";
import { useBrand } from "@/context/useBrand";
import { StatTile } from "@/components/cx/StatTile";
import { FunnelBars } from "@/components/cx/FunnelBars";
import { Gauge } from "@/components/cx/Gauge";
import { SourceBadge } from "@/components/cx/SourceBadge";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import {
  Radio,
  Sparkles,
  ArrowRight,
  Play,
  ExternalLink,
  Activity,
  Award,
  AlertTriangle,
  FolderPlus,
} from "lucide-react";
import { cn } from "@/lib/utils";

export function OverviewPage() {
  const { activeBrand } = useBrand();

  // Query Brand Summary
  const {
    data: summary,
    isLoading: isLoadingSummary,
    isError: isSummaryError,
    error: summaryError,
    refetch: refetchSummary,
  } = useQuery({
    queryKey: ["brand-summary", activeBrand?.id],
    queryFn: () => (activeBrand ? apiClient.getBrandSummary(activeBrand.id) : null),
    enabled: !!activeBrand,
  });

  // Query Last Scan detail for live events feed
  const lastScanId = summary?.last_scan?.id;
  const { data: lastScan } = useQuery({
    queryKey: ["scan", lastScanId],
    queryFn: () => (lastScanId ? apiClient.getScan(lastScanId) : null),
    enabled: !!lastScanId,
  });

  // Compute time of day greeting
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 17) return "Good afternoon";
    return "Good evening";
  };

  // Check if brand is empty
  const isEmptyBrand =
    summary &&
    summary.official_asset_count === 0 &&
    (!summary.last_scan || summary.funnel.retrieved === 0);

  if (isLoadingSummary) {
    return (
      <div className="space-y-6 animate-pulse" aria-busy="true">
        <div className="h-32 bg-ink/10 rounded-panel" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 bg-surface rounded-panel border border-hairline" />
          ))}
        </div>
        <div className="h-64 bg-surface rounded-panel border border-hairline" />
      </div>
    );
  }

  // Guided Empty State
  if (isEmptyBrand) {
    return (
      <div className="space-y-6">
        <div className="p-12 rounded-panel bg-surface border border-hairline text-center max-w-xl mx-auto space-y-4 mt-8 shadow-xs">
          <div className="w-12 h-12 rounded-full bg-lens/10 text-lens flex items-center justify-center mx-auto">
            <FolderPlus className="w-6 h-6" />
          </div>
          <h2 className="font-display font-bold text-xl text-ink">Welcome to ThreatLens</h2>
          <p className="text-xs text-ink-muted leading-relaxed">
            Register an official asset, then run a scan. ThreatLens uses official registered assets as the truth anchor for lookalike and impersonation detection.
          </p>
          <div className="flex items-center justify-center gap-3 pt-2">
            <Link
              to="/brand"
              className="px-4 py-2 text-xs font-semibold rounded-pill bg-ink text-white hover:bg-ink/90 flex items-center gap-1.5 shadow-sm"
            >
              <span>Add Official Asset</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
            <Link
              to="/scan"
              className="px-4 py-2 text-xs font-semibold rounded-pill bg-surface-2 hover:bg-surface border border-hairline text-ink transition-colors"
            >
              <span>Scan Setup</span>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (isSummaryError || !summary || !activeBrand) {
    return (
      <div className="p-8 rounded-panel bg-surface border border-hairline text-center space-y-3 max-w-lg mx-auto">
        <AlertTriangle className="w-6 h-6 text-risk-critical mx-auto" />
        <h3 className="font-semibold text-xs text-ink">Failed to load brand summary</h3>
        <p className="text-xs text-ink-muted">
          {summaryError instanceof ApiError ? summaryError.message : "Please select an active brand or verify network connection."}
        </p>
        {summaryError instanceof ApiError && summaryError.requestId && (
          <span className="font-mono text-[10px] text-ink-muted block">
            Request ID: {summaryError.requestId}
          </span>
        )}
        <button
          onClick={() => refetchSummary()}
          className="mt-2 px-3 py-1.5 rounded-pill bg-ink text-white text-xs font-semibold hover:bg-ink/90 transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  // Severity Distribution data for Recharts
  const severityData = [
    { name: "CRITICAL", count: summary.findings_by_severity.CRITICAL, color: "#A4123F" },
    { name: "HIGH", count: summary.findings_by_severity.HIGH, color: "#D9480F" },
    { name: "MEDIUM", count: summary.findings_by_severity.MEDIUM, color: "#B7791F" },
    { name: "LOW", count: summary.findings_by_severity.LOW, color: "#55627F" },
  ];

  // Cleared rules count
  const clearedTotal =
    (summary.funnel.official_cleared || 0) + (summary.funnel.benign_lookalike || 0);

  return (
    <div className="space-y-6 animate-fade-in pb-16">
      {/* 1. Black Greeting Banner */}
      <div className="p-6 rounded-panel bg-ink text-white shadow-md relative overflow-hidden space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 relative z-10">
          <div className="space-y-1">
            <h1 className="font-display font-bold text-2xl sm:text-3xl tracking-tight text-white">
              {getGreeting()}, {activeBrand.name}
            </h1>
            <p className="text-xs text-white/75 max-w-xl">
              Forensic brand defense workspace. Continuous detection against App Store impersonators and social spoofing.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <Link
              to="/scan"
              className="px-4 py-2 text-xs font-semibold rounded-pill bg-white text-ink hover:bg-white/90 flex items-center gap-2 shadow-sm transition-all"
            >
              <Play className="w-3.5 h-3.5 fill-ink" />
              <span>Start scan</span>
            </Link>
          </div>
        </div>

        {/* DemoBanner text integrated into greeting banner when demo_brand */}
        {activeBrand.demo_brand && (
          <div className="pt-3 border-t border-white/15 flex items-center gap-2 text-xs text-amber-200 font-medium">
            <Sparkles className="w-4 h-4 text-amber-300 shrink-0" />
            <span>
              Demo brand {activeBrand.name}: mock catalogs and synthetic candidates active for demonstration.
            </span>
          </div>
        )}
      </div>

      {/* 2. KPI Tiles */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Link to="/findings" className="block group">
          <StatTile
            label="Candidates for review"
            value={summary.funnel.findings}
            hint="Active unresolved alerts"
            className="group-hover:border-lens transition-colors"
          />
        </Link>

        <Link to="/cleared" className="block group">
          <StatTile
            label="Cleared by rules"
            value={clearedTotal}
            hint="IdentityGuard & Gates"
            className="group-hover:border-lens transition-colors"
          />
        </Link>

        <Link to="/brand" className="block group">
          <StatTile
            label="Official assets registered"
            value={summary.official_asset_count}
            hint="Anchor identifiers"
            className="group-hover:border-lens transition-colors"
          />
        </Link>

        <Link
          to={summary.last_scan ? `/scan/${summary.last_scan.id}` : "/scan"}
          className="block group"
        >
          <div className="p-4 rounded-panel border border-hairline bg-surface shadow-xs space-y-1.5 h-full group-hover:border-lens transition-colors">
            <span className="text-[11px] font-medium text-ink-muted block">
              Last Scan
            </span>
            <div className="flex items-center gap-2">
              <span className="font-display font-bold text-xl text-ink">
                {summary.last_scan?.mode || "None"}
              </span>
              {summary.last_scan && (
                <span className="font-mono text-[10px] px-2 py-0.5 rounded-pill bg-teal-500/10 text-teal-700 dark:text-teal-400 border border-teal-500/25 font-semibold uppercase">
                  {summary.last_scan.status}
                </span>
              )}
            </div>
            <span className="text-[11px] font-mono text-ink-muted block truncate">
              {summary.last_scan?.completed_at
                ? new Date(summary.last_scan.completed_at).toLocaleString([], {
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })
                : "No completed scans"}
            </span>
          </div>
        </Link>
      </div>

      {/* 3. Detection Funnel & Invariant Note */}
      <div className="rounded-panel border border-hairline bg-surface p-5 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-display font-semibold text-base text-ink">
            Detection & Filtering Funnel
          </h2>
          <span className="font-mono text-xs text-ink-muted">
            Total retrieved: {summary.funnel.retrieved}
          </span>
        </div>
        <FunnelBars funnel={summary.funnel} />
      </div>

      {/* 4. Multi-metric Middle Grid: Severity Distribution | Review Progress Gauge | Latest Eval */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">
        {/* Severity Distribution (Recharts Bar) */}
        <div className="rounded-panel border border-hairline bg-surface p-5 shadow-xs space-y-3 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <h3 className="font-display font-semibold text-sm text-ink">
              Severity Distribution
            </h3>
            <span className="text-xs text-ink-muted font-mono">
              {summary.funnel.findings} total
            </span>
          </div>

          <div className="h-44 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={severityData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#55627F" }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: "#55627F" }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#FFFFFF",
                    borderRadius: 8,
                    borderColor: "#E3E5EE",
                    fontSize: 12,
                  }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {severityData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="flex items-center justify-between text-[11px] text-ink-muted pt-2 border-t border-hairline">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#A4123F]" /> Critical: {summary.findings_by_severity.CRITICAL}
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#D9480F]" /> High: {summary.findings_by_severity.HIGH}
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#B7791F]" /> Medium: {summary.findings_by_severity.MEDIUM}
            </span>
          </div>
        </div>

        {/* Review Progress Semicircle Gauge */}
        <div className="rounded-panel border border-hairline bg-surface p-5 shadow-xs space-y-3 flex flex-col items-center justify-between">
          <div className="w-full flex items-center justify-between">
            <h3 className="font-display font-semibold text-sm text-ink">
              Analyst Review Progress
            </h3>
            <span className="font-mono text-xs text-ink-muted">
              {summary.review_progress.reviewed} / {summary.review_progress.total}
            </span>
          </div>

          <div className="my-auto py-2">
            <Gauge
              value={summary.review_progress.reviewed}
              max={Math.max(1, summary.review_progress.total)}
              label="Review progress"
              hideProbabilityNote={true}
              subtitle="Decisions recorded"
              size={170}
            />
          </div>

          <p className="text-[11px] text-ink-muted text-center leading-tight">
            Percentage of candidates confirmed, dismissed, or marked inconclusive.
          </p>
        </div>

        {/* Latest Evaluation Card */}
        <div className="rounded-panel border border-hairline bg-surface p-5 shadow-xs space-y-3 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <h3 className="font-display font-semibold text-sm text-ink">
              Latest Evaluation
            </h3>
            <Award className="w-4 h-4 text-lens" />
          </div>

          {summary.latest_evaluation &&
          summary.latest_evaluation.precision !== null &&
          summary.latest_evaluation.recall !== null ? (
            <div className="space-y-3 py-1">
              <div className="p-3 rounded-panel-nested bg-surface-2 border border-hairline space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-ink-muted">Test Split:</span>
                  <span className="font-mono font-bold text-ink">
                    {summary.latest_evaluation.split || "HELDOUT"}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-[10px] text-ink-muted uppercase block">Precision</span>
                    <span className="font-mono font-bold text-base text-teal-700 dark:text-teal-400">
                      {(summary.latest_evaluation.precision * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-ink-muted uppercase block">Recall</span>
                    <span className="font-mono font-bold text-base text-lens">
                      {(summary.latest_evaluation.recall * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
                {summary.latest_evaluation.created_at && (
                  <span className="text-[10px] text-ink-muted block font-mono">
                    Run: {new Date(summary.latest_evaluation.created_at).toLocaleDateString()}
                  </span>
                )}
              </div>
              <Link
                to="/evaluation"
                className="text-xs text-lens hover:underline font-semibold flex items-center gap-1 justify-end"
              >
                <span>Open Evaluation Lab</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          ) : (
            <div className="space-y-3 py-6 text-center">
              <p className="text-xs text-ink-muted">No evaluation run yet.</p>
              <Link
                to="/evaluation"
                className="inline-flex items-center gap-1 text-xs text-lens font-semibold hover:underline"
              >
                <span>Run benchmark evaluation</span>
                <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
          )}

          <div className="pt-2 border-t border-hairline text-[11px] text-ink-muted">
            Independent benchmark metrics against labelled synthetic & captured corpora.
          </div>
        </div>
      </div>

      {/* 5. Platforms & Status Breakdowns */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Findings by Platform */}
        <div className="rounded-panel border border-hairline bg-surface p-5 shadow-xs space-y-3">
          <h3 className="font-display font-semibold text-sm text-ink">
            Findings by Platform
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
            {Object.entries(summary.findings_by_platform).map(([plat, count]) => (
              <div
                key={plat}
                className="p-2.5 rounded-panel-nested bg-surface-2 border border-hairline flex items-center justify-between"
              >
                <span className="font-mono text-[11px] text-ink truncate mr-2">
                  {plat}
                </span>
                <span className="font-mono font-bold text-ink">{count}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Findings by Status */}
        <div className="rounded-panel border border-hairline bg-surface p-5 shadow-xs space-y-3">
          <h3 className="font-display font-semibold text-sm text-ink">
            Findings by Status
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
            {Object.entries(summary.findings_by_status).map(([st, count]) => (
              <div
                key={st}
                className="p-2.5 rounded-panel-nested bg-surface-2 border border-hairline space-y-1"
              >
                <span className="text-[10px] text-ink-muted block uppercase truncate">
                  {st.replace(/_/g, " ")}
                </span>
                <span className="font-mono font-bold text-sm text-ink block">{count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 6. Source Coverage Strip */}
      <div className="rounded-panel border border-hairline bg-surface p-5 shadow-xs space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Radio className="w-4 h-4 text-teal-600" />
            <h3 className="font-display font-semibold text-sm text-ink">
              Source Coverage Strip
            </h3>
          </div>
          <Link
            to="/sources"
            className="text-xs text-lens font-semibold hover:underline flex items-center gap-1"
          >
            <span>View All Providers</span>
            <ExternalLink className="w-3 h-3" />
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          {summary.source_coverage.map((sc) => (
            <div
              key={sc.source_id}
              className="p-3 rounded-panel-nested bg-surface-2 border border-hairline flex items-center justify-between gap-2"
            >
              <div>
                <span className="font-mono font-semibold text-ink block">
                  {sc.source_id}
                </span>
                <span className="text-[10px] text-ink-muted block font-mono">
                  {sc.retrieved_at
                    ? new Date(sc.retrieved_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })
                    : "Not retrieved"}
                </span>
              </div>
              <SourceBadge mode={sc.source_mode || "LIVE"} />
            </div>
          ))}
        </div>
      </div>

      {/* 7. Last Scan Live Event Feed */}
      {lastScan?.events && lastScan.events.length > 0 && (
        <div className="rounded-panel border border-hairline bg-surface p-5 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-ink" />
              <h3 className="font-display font-semibold text-sm text-ink">
                Last Scan Pipeline Event Feed
              </h3>
            </div>
            <span className="font-mono text-xs text-ink-muted">
              Scan ID: {lastScan.id}
            </span>
          </div>

          <div className="space-y-1.5 max-h-48 overflow-y-auto font-mono text-xs p-3 rounded-nested bg-surface-2 border border-hairline divide-y divide-hairline">
            {lastScan.events.map((ev, idx) => (
              <div key={idx} className="py-1.5 flex items-start gap-2.5">
                <span className="text-[10px] text-ink-muted shrink-0">
                  {new Date(ev.at).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                  })}
                </span>
                <span
                  className={cn(
                    "text-[10px] px-1.5 py-0.2 rounded font-bold uppercase shrink-0",
                    ev.level === "ERROR"
                      ? "bg-risk-critical/10 text-risk-critical"
                      : ev.level === "WARNING"
                      ? "bg-risk-medium/10 text-risk-medium"
                      : "bg-surface text-ink-muted border border-hairline"
                  )}
                >
                  {ev.level}
                </span>
                <span className="text-ink text-[11px] leading-tight">
                  [{ev.stage}] {ev.message}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
