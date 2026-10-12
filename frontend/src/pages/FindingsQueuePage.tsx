import React, { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import { useBrand } from "@/context/useBrand";
import type { Schema } from "@/api/client";
import { ApiError } from "@/api/errors";
import { ScoreBar } from "@/components/cx/ScoreBar";
import { SeverityPill } from "@/components/cx/SeverityPill";
import { StatusPill } from "@/components/cx/StatusPill";
import { SourceBadge } from "@/components/cx/SourceBadge";
import { AssetIcon } from "@/components/cx/AssetIcon";
import { DecisionDialog } from "./findings/DecisionDialog";
import { PeekDrawer } from "./findings/PeekDrawer";
import {
  Search,
  CheckCircle2,
  AlertTriangle,
  Eye,
  Check,
  X,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  ArrowRight,
  RefreshCw,
} from "lucide-react";
import { cn } from "@/lib/utils";

export function FindingsQueuePage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { activeBrand } = useBrand();
  const queryClient = useQueryClient();

  // Read URL query parameters
  const scanId = searchParams.get("scan_id") || undefined;
  const statusParam = (searchParams.get("status") || "ALL") as string;
  const assetTypeTab = (searchParams.get("asset_tab") || "ALL") as "ALL" | "APPS" | "SOCIAL";
  const platformParam = (searchParams.get("platform") || "ALL") as string;
  const severityParam = (searchParams.get("severity") || "ALL") as string;
  const minScoreParam = Number(searchParams.get("min_score") || "0");
  const sourceModeParam = (searchParams.get("source_mode") || "ALL") as string;
  const queryParam = searchParams.get("q") || "";
  const sortParam = (searchParams.get("sort") || "score_desc") as
    | "score_desc"
    | "score_asc"
    | "seen_desc"
    | "name_asc";
  const includeDismissed = searchParams.get("include_dismissed") === "true";
  const pageParam = Math.max(1, Number(searchParams.get("page") || "1"));
  const limit = 20;
  const offset = (pageParam - 1) * limit;

  // Modals state
  const [decisionFinding, setDecisionFinding] = useState<Schema["FindingListItem"] | null>(null);
  const [decisionInitialStatus, setDecisionInitialStatus] = useState<Schema["FindingStatus"]>("IN_REVIEW");
  const [peekFindingId, setPeekFindingId] = useState<string | null>(null);

  // Helper to update query string
  const updateQuery = (updates: Record<string, string | null>) => {
    const next = new URLSearchParams(searchParams);
    for (const [key, val] of Object.entries(updates)) {
      if (val === null || val === "" || val === "ALL" || (key === "page" && val === "1")) {
        next.delete(key);
      } else {
        next.set(key, val);
      }
    }
    setSearchParams(next, { replace: true });
  };

  // Convert tab to API asset_type parameter
  const apiAssetType: Schema["AssetType"] | undefined =
    assetTypeTab === "SOCIAL"
      ? "SOCIAL_ACCOUNT"
      : assetTypeTab === "APPS"
      ? "IOS_APP"
      : undefined;

  // Query findings
  const {
    data: findingsData,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: [
      "findings",
      activeBrand?.id,
      scanId,
      statusParam,
      assetTypeTab,
      platformParam,
      severityParam,
      minScoreParam,
      sourceModeParam,
      queryParam,
      sortParam,
      includeDismissed,
      offset,
    ],
    queryFn: () => {
      if (!activeBrand) return null;
      return apiClient.getFindings({
        brand_id: activeBrand.id,
        scan_id: scanId,
        status: statusParam === "ALL" ? undefined : (statusParam as Schema["FindingStatus"]),
        asset_type: apiAssetType,
        platform: platformParam === "ALL" ? undefined : platformParam,
        severity: severityParam === "ALL" ? undefined : (severityParam as Schema["Severity"]),
        min_score: minScoreParam > 0 ? minScoreParam : undefined,
        source_mode: sourceModeParam === "ALL" ? undefined : (sourceModeParam as Schema["SourceMode"]),
        q: queryParam.trim() || undefined,
        include_dismissed: includeDismissed,
        sort: sortParam,
        limit,
        offset,
      });
    },
    enabled: !!activeBrand,
  });

  // Query brand summary for cleared counts
  const { data: brandSummary } = useQuery({
    queryKey: ["brand-summary", activeBrand?.id],
    queryFn: () => (activeBrand ? apiClient.getBrandSummary(activeBrand.id) : null),
    enabled: !!activeBrand,
  });

  // Quick set IN_REVIEW mutation
  const inReviewMutation = useMutation({
    mutationFn: (findingId: string) => {
      return apiClient.patchFinding(findingId, {
        status: "IN_REVIEW",
        notes: "Marked in review from findings queue action.",
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["findings"] });
      queryClient.invalidateQueries({ queryKey: ["brand-summary"] });
    },
  });

  const findings = findingsData?.items || [];
  const totalFindings = findingsData?.total || 0;
  const totalPages = Math.ceil(totalFindings / limit) || 1;

  // Cleared count from summary or scan
  const clearedCount = brandSummary?.funnel.official_cleared ?? 5;

  return (
    <div className="space-y-6 animate-fade-in pb-16">
      {/* Header Strip with Cleared Rules Counter */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-hairline">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="font-display font-bold text-2xl text-ink tracking-tight">
              Findings Review Queue
            </h1>
            <span className="font-mono text-xs px-2.5 py-0.5 rounded-full bg-surface-2 text-ink border border-hairline font-semibold">
              {totalFindings} candidates
            </span>
            {scanId && (
              <span className="font-mono text-xs px-2.5 py-0.5 rounded-full bg-lens/10 text-lens border border-lens/20 font-semibold">
                Scan: {scanId}
              </span>
            )}
          </div>
          <p className="text-xs text-ink-muted mt-1">
            Unresolved candidates evaluated against official assets across 7 observable signals.
          </p>
        </div>

        {/* Visible link "N cleared by rules" to /cleared */}
        <div className="flex items-center gap-3">
          <Link
            to={scanId ? `/cleared?scan_id=${scanId}` : "/cleared"}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-pill bg-[#0E8F9C]/10 hover:bg-[#0E8F9C]/15 text-[#0E8F9C] border border-[#0E8F9C]/30 text-xs font-semibold transition-colors shadow-xs"
            title="Official assets cleared by exact identity rules"
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>{clearedCount} cleared by rules</span>
            <ArrowRight className="w-3 h-3 ml-0.5" />
          </Link>

          <button
            onClick={() => refetch()}
            className="p-1.5 rounded-panel-nested border border-hairline hover:bg-surface-2 text-ink-muted hover:text-ink transition-colors"
            title="Refresh findings queue"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Tabs: All / Apps / Social accounts */}
      <div className="flex items-center gap-1 border-b border-hairline pb-px text-xs font-semibold">
        {[
          { id: "ALL", label: "All Candidates" },
          { id: "APPS", label: "Store Apps (iOS & Android)" },
          { id: "SOCIAL", label: "Social Accounts (Bluesky)" },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => updateQuery({ asset_tab: tab.id, page: "1" })}
            className={cn(
              "px-4 py-2 border-b-2 transition-colors",
              assetTypeTab === tab.id
                ? "border-lens text-ink font-bold"
                : "border-transparent text-ink-muted hover:text-ink hover:border-hairline"
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Filter Toolbar (Synced to URL Query String) */}
      <div className="rounded-panel border border-hairline bg-surface p-4 shadow-sm space-y-3 text-xs">
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Search Box */}
          <div className="relative min-w-[200px] flex-1">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-ink-muted" />
            <input
              type="text"
              value={queryParam}
              onChange={(e) => updateQuery({ q: e.target.value, page: "1" })}
              placeholder="Filter by name, handle, or publisher..."
              className="w-full pl-8 pr-3 py-1.5 rounded-panel-nested border border-hairline bg-surface-2 text-ink text-xs focus:outline-none focus:ring-1 focus:ring-lens"
            />
          </div>

          {/* Severity */}
          <select
            value={severityParam}
            onChange={(e) => updateQuery({ severity: e.target.value, page: "1" })}
            className="px-2.5 py-1.5 rounded-panel-nested border border-hairline bg-surface-2 text-ink text-xs focus:outline-none focus:ring-1 focus:ring-lens"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>

          {/* Status */}
          <select
            value={statusParam}
            onChange={(e) => updateQuery({ status: e.target.value, page: "1" })}
            className="px-2.5 py-1.5 rounded-panel-nested border border-hairline bg-surface-2 text-ink text-xs focus:outline-none focus:ring-1 focus:ring-lens"
          >
            <option value="ALL">All Review Statuses</option>
            <option value="NEW">New</option>
            <option value="IN_REVIEW">In Review</option>
            <option value="CONFIRMED_SUSPICIOUS">Confirmed Suspicious</option>
            <option value="DISMISSED_FALSE_POSITIVE">Dismissed</option>
            <option value="INCONCLUSIVE">Inconclusive</option>
          </select>

          {/* Platform */}
          <select
            value={platformParam}
            onChange={(e) => updateQuery({ platform: e.target.value, page: "1" })}
            className="px-2.5 py-1.5 rounded-panel-nested border border-hairline bg-surface-2 text-ink text-xs focus:outline-none focus:ring-1 focus:ring-lens"
          >
            <option value="ALL">All Platforms</option>
            <option value="apple_app_store">Apple App Store</option>
            <option value="bluesky">Bluesky</option>
            <option value="google_play">Google Play</option>
            <option value="instagram">Instagram</option>
            <option value="x">X</option>
            <option value="facebook">Facebook</option>
          </select>

          {/* Source Mode */}
          <select
            value={sourceModeParam}
            onChange={(e) => updateQuery({ source_mode: e.target.value, page: "1" })}
            className="px-2.5 py-1.5 rounded-panel-nested border border-hairline bg-surface-2 text-ink text-xs focus:outline-none focus:ring-1 focus:ring-lens"
          >
            <option value="ALL">All Source Modes</option>
            <option value="LIVE">Live</option>
            <option value="CACHED">Cached</option>
            <option value="SIMULATED">Simulated</option>
          </select>

          {/* Sort */}
          <select
            value={sortParam}
            onChange={(e) => updateQuery({ sort: e.target.value, page: "1" })}
            className="px-2.5 py-1.5 rounded-panel-nested border border-hairline bg-surface-2 text-ink text-xs focus:outline-none focus:ring-1 focus:ring-lens font-mono"
          >
            <option value="score_desc">Sort: Risk Score (High → Low)</option>
            <option value="score_asc">Sort: Risk Score (Low → High)</option>
            <option value="seen_desc">Sort: Recently Observed</option>
            <option value="name_asc">Sort: Candidate Name (A → Z)</option>
          </select>
        </div>

        {/* Secondary Toggles & Min Score */}
        <div className="flex flex-wrap items-center justify-between gap-4 pt-2 border-t border-hairline/60">
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 cursor-pointer text-ink text-xs font-medium">
              <input
                type="checkbox"
                checked={includeDismissed}
                onChange={(e) =>
                  updateQuery({ include_dismissed: e.target.checked ? "true" : null, page: "1" })
                }
                className="w-3.5 h-3.5 rounded text-lens"
              />
              <span>Include dismissed false positives</span>
            </label>

            {scanId && (
              <button
                onClick={() => updateQuery({ scan_id: null, page: "1" })}
                className="text-[11px] text-lens hover:underline font-medium"
              >
                Clear scan filter ({scanId})
              </button>
            )}
          </div>

          {/* Reset Filters */}
          {(statusParam !== "ALL" ||
            platformParam !== "ALL" ||
            severityParam !== "ALL" ||
            sourceModeParam !== "ALL" ||
            queryParam !== "" ||
            includeDismissed) && (
            <button
              onClick={() => {
                setSearchParams(new URLSearchParams(), { replace: true });
              }}
              className="text-[11px] text-ink-muted hover:text-ink underline"
            >
              Reset all filters
            </button>
          )}
        </div>
      </div>

      {/* Main Table Content */}
      <div className="rounded-panel border border-hairline bg-surface shadow-sm overflow-hidden">
        {/* Error State */}
        {isError ? (
          <div className="p-8 text-center space-y-2">
            <AlertTriangle className="w-6 h-6 text-risk-critical mx-auto" />
            <h3 className="font-semibold text-xs text-ink">Failed to load findings queue</h3>
            <p className="text-xs text-ink-muted">
              {error instanceof ApiError ? error.message : "Network error retrieving findings."}
            </p>
            {error instanceof ApiError && error.requestId && (
              <span className="font-mono text-[10px] text-ink-muted block">
                Request ID: {error.requestId}
              </span>
            )}
            <button
              onClick={() => refetch()}
              className="mt-2 px-3 py-1 rounded-pill bg-ink text-white text-xs font-semibold"
            >
              Retry
            </button>
          </div>
        ) : isLoading ? (
          /* Loading Skeletons */
          <div className="p-6 space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div
                key={i}
                className="h-16 w-full rounded-panel-nested bg-surface-2 animate-pulse"
              />
            ))}
          </div>
        ) : findings.length === 0 ? (
          /* Empty State (Section 15.3 copy) */
          <div className="p-16 text-center space-y-2">
            <CheckCircle2 className="w-8 h-8 text-[#0E8F9C] mx-auto" />
            <h3 className="font-display font-semibold text-sm text-ink">
              No candidates for review match the selected filters.
            </h3>
            <p className="text-xs text-ink-muted max-w-sm mx-auto">
              All observed items were either cleared by exact IdentityGuard rules, evaluated below threshold, or filtered out by current criteria.
            </p>
            {(statusParam !== "ALL" ||
              platformParam !== "ALL" ||
              severityParam !== "ALL" ||
              queryParam !== "") && (
              <button
                onClick={() => setSearchParams(new URLSearchParams(), { replace: true })}
                className="mt-2 px-3 py-1.5 rounded-pill bg-ink text-white text-xs font-semibold hover:bg-ink/90 transition-colors"
              >
                Clear Active Filters
              </button>
            )}
          </div>
        ) : (
          /* Findings Table */
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-surface-2 text-ink-muted border-b border-hairline text-[11px] font-medium">
                  <th className="py-2.5 px-4 w-10">Icon</th>
                  <th className="py-2.5 px-4">Candidate Name</th>
                  <th className="py-2.5 px-4">Platform</th>
                  <th className="py-2.5 px-4 min-w-[140px]">Risk Score</th>
                  <th className="py-2.5 px-4 min-w-[200px]">Why Flagged (Top Signals)</th>
                  <th className="py-2.5 px-4">Technique</th>
                  <th className="py-2.5 px-4">Status</th>
                  <th className="py-2.5 px-4">Source</th>
                  <th className="py-2.5 px-4">Observed</th>
                  <th className="py-2.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline">
                {findings.map((item) => {
                  const topTwo = item.top_signals.slice(0, 2);

                  return (
                    <tr
                      key={item.id}
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          navigate(`/findings/${item.id}`);
                        }
                      }}
                      className="hover:bg-surface-2/50 focus:bg-surface-2/60 transition-colors focus:outline-none focus:ring-1 focus:ring-lens"
                    >
                      {/* Icon */}
                      <td className="py-3 px-4">
                        <AssetIcon
                          src={item.candidate.icon_url || undefined}
                          alt={item.candidate.display_name}
                          size="sm"
                        />
                      </td>

                      {/* Name (+ handle or publisher) */}
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-1.5">
                          <Link
                            to={`/findings/${item.id}`}
                            className="font-semibold text-ink hover:text-lens hover:underline block leading-snug"
                          >
                            {item.candidate.display_name}
                          </Link>
                          {item.changed_since_decision && (
                            <span
                              className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-amber-100 text-amber-800 border border-amber-300 shrink-0"
                              title="Observable attributes modified since last analyst verdict"
                            >
                              CHANGED
                            </span>
                          )}
                        </div>
                        <span className="text-[11px] text-ink-muted block truncate max-w-[180px]">
                          {item.candidate.handle
                            ? `@${item.candidate.handle}`
                            : item.candidate.publisher_name || "—"}
                        </span>
                      </td>

                      {/* Platform */}
                      <td className="py-3 px-4">
                        <span className="font-mono text-[11px] text-ink px-1.5 py-0.5 rounded bg-surface-2 border border-hairline">
                          {item.candidate.platform}
                        </span>
                      </td>

                      {/* Risk Score */}
                      <td className="py-3 px-4">
                        <div className="space-y-1">
                          <div className="flex items-center justify-between">
                            <SeverityPill severity={item.severity} />
                            <span className="font-mono text-ink text-xs font-bold">
                              {item.risk_score}/100
                            </span>
                          </div>
                          <ScoreBar value={item.risk_score} max={100} />
                        </div>
                      </td>

                      {/* Why Flagged (Top Two Signals) */}
                      <td className="py-3 px-4">
                        <div className="space-y-1">
                          {topTwo.map((sig) => (
                            <div
                              key={sig.signal}
                              className="text-[11px] flex items-center justify-between gap-2"
                            >
                              <span className="font-mono text-ink truncate max-w-[150px]">
                                {sig.signal}
                              </span>
                              <span className="font-mono font-bold text-ink shrink-0">
                                +{sig.points} pts
                              </span>
                            </div>
                          ))}
                        </div>
                      </td>

                      {/* Technique */}
                      <td className="py-3 px-4">
                        <span className="font-mono text-[11px] text-ink-muted px-1.5 py-0.5 rounded bg-surface-2 border border-hairline">
                          {item.technique}
                        </span>
                      </td>

                      {/* Status Pill */}
                      <td className="py-3 px-4">
                        <StatusPill status={item.status} />
                      </td>

                      {/* Source Badge */}
                      <td className="py-3 px-4">
                        <SourceBadge status={item.source_mode} />
                      </td>

                      {/* Observed At */}
                      <td className="py-3 px-4 whitespace-nowrap text-[11px] text-ink-muted">
                        {new Date(item.observed_at).toLocaleDateString([], {
                          month: "short",
                          day: "numeric",
                        })}
                      </td>

                      {/* Actions */}
                      <td className="py-3 px-4 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-1">
                          {/* Peek Drawer Action */}
                          <button
                            type="button"
                            onClick={() => setPeekFindingId(item.id)}
                            className="p-1.5 text-ink-muted hover:text-ink hover:bg-surface-2 rounded-panel-nested transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-lens"
                            title="Peek score breakdown"
                            aria-label={`Peek score breakdown for ${item.candidate.name}`}
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>

                          {/* Quick Set IN_REVIEW */}
                          {item.status === "NEW" && (
                            <button
                              type="button"
                              onClick={() => inReviewMutation.mutate(item.id)}
                              disabled={inReviewMutation.isPending}
                              className="px-2 py-1 text-[11px] font-semibold text-lens bg-lens/10 hover:bg-lens/20 rounded-panel-nested transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-lens"
                              title="Mark in review"
                              aria-label={`Mark ${item.candidate.name} in review`}
                            >
                              Review
                            </button>
                          )}

                          {/* Dismiss Dialog */}
                          <button
                            type="button"
                            onClick={() => {
                              setDecisionFinding(item);
                              setDecisionInitialStatus("DISMISSED_FALSE_POSITIVE");
                            }}
                            className="p-1.5 text-ink-muted hover:text-emerald-700 hover:bg-emerald-50 rounded-panel-nested transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-lens"
                            title="Dismiss false positive (opens decision dialog)"
                            aria-label={`Dismiss ${item.candidate.name} as false positive`}
                          >
                            <Check className="w-3.5 h-3.5" />
                          </button>

                          {/* Confirm Dialog */}
                          <button
                            type="button"
                            onClick={() => {
                              setDecisionFinding(item);
                              setDecisionInitialStatus("CONFIRMED_SUSPICIOUS");
                            }}
                            className="p-1.5 text-ink-muted hover:text-risk-high hover:bg-risk-high/10 rounded-panel-nested transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-lens"
                            title="Confirm suspicious (opens decision dialog)"
                            aria-label={`Confirm ${item.candidate.name} as suspicious`}
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>

                          {/* Open Detail Page */}
                          <Link
                            to={`/findings/${item.id}`}
                            className="ml-1 px-2.5 py-1 text-[11px] font-semibold text-ink hover:bg-surface-2 border border-hairline rounded-pill transition-colors inline-flex items-center gap-1"
                            title="Open full evidence compare"
                          >
                            <span>Compare</span>
                            <ArrowRight className="w-3 h-3" />
                          </Link>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        {totalFindings > limit && (
          <div className="p-4 border-t border-hairline bg-surface-2 flex items-center justify-between text-xs">
            <span className="text-ink-muted">
              Showing {offset + 1}–{Math.min(offset + limit, totalFindings)} of {totalFindings} candidates
            </span>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => updateQuery({ page: String(pageParam - 1) })}
                disabled={pageParam <= 1}
                className="p-1.5 rounded-panel-nested border border-hairline bg-surface hover:bg-surface-2 disabled:opacity-40 transition-colors"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
              </button>
              <span className="font-mono text-ink font-semibold">
                Page {pageParam} of {totalPages}
              </span>
              <button
                type="button"
                onClick={() => updateQuery({ page: String(pageParam + 1) })}
                disabled={pageParam >= totalPages}
                className="p-1.5 rounded-panel-nested border border-hairline bg-surface hover:bg-surface-2 disabled:opacity-40 transition-colors"
              >
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Peek Drawer */}
      <PeekDrawer
        findingId={peekFindingId}
        onClose={() => setPeekFindingId(null)}
        onOpenDecision={(f) => {
          setDecisionFinding(f);
          setDecisionInitialStatus("IN_REVIEW");
        }}
      />

      {/* Decision Dialog */}
      <DecisionDialog
        open={!!decisionFinding}
        onOpenChange={(open) => !open && setDecisionFinding(null)}
        finding={decisionFinding}
        initialStatus={decisionInitialStatus}
      />
    </div>
  );
}
