import React from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import { useBrand } from "@/context/useBrand";
import type { Schema } from "@/api/client";
import { SourceBadge } from "@/components/cx/SourceBadge";
import { AssetIcon } from "@/components/cx/AssetIcon";
import {
  Search,
  RotateCcw,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Info,
  CheckCircle2,
} from "lucide-react";
import { cn } from "@/lib/utils";

export function ClearedItemsPage() {
  const { activeBrand } = useBrand();
  const [searchParams, setSearchParams] = useSearchParams();

  // Read URL parameters
  const decisionParam = searchParams.get("decision") || "ALL";
  const platformParam = searchParams.get("platform") || "ALL";
  const scanIdParam = searchParams.get("scan_id") || undefined;
  const queryParam = searchParams.get("q") || "";
  const pageParam = Math.max(1, Number(searchParams.get("page") || "1"));
  const limit = 20;
  const offset = (pageParam - 1) * limit;

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

  const {
    data: clearedData,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: [
      "cleared",
      activeBrand?.id,
      decisionParam,
      platformParam,
      scanIdParam,
      queryParam,
      offset,
    ],
    queryFn: () => {
      if (!activeBrand) return null;
      return apiClient.getCleared(activeBrand.id, {
        decision:
          decisionParam === "ALL"
            ? undefined
            : (decisionParam as Schema["IdentityDecision"]),
        platform: platformParam === "ALL" ? undefined : platformParam,
        scan_id: scanIdParam,
        q: queryParam.trim() || undefined,
        limit,
        offset,
      });
    },
    enabled: !!activeBrand,
  });

  const items = clearedData?.items || [];
  const totalItems = clearedData?.total || 0;
  const totalPages = Math.ceil(totalItems / limit) || 1;

  // Decision tabs
  const decisionTabs: Array<{ id: string; label: string; ruleHint: string }> = [
    { id: "ALL", label: "All Cleared", ruleHint: "All rules" },
    {
      id: "OFFICIAL_EXACT_MATCH",
      label: "Official Exact ID",
      ruleHint: "Rule R1",
    },
    {
      id: "OFFICIAL_PUBLISHER_MATCH",
      label: "Official Publisher ID",
      ruleHint: "Rule R2",
    },
    {
      id: "AUTHORIZED_PARTNER_MATCH",
      label: "Authorized Partner",
      ruleHint: "Rule R3",
    },
    {
      id: "BENIGN_LOOKALIKE",
      label: "Benign Lookalike",
      ruleHint: "Gates G4 / G5",
    },
    {
      id: "BELOW_THRESHOLD",
      label: "Below Threshold",
      ruleHint: "Score < 25",
    },
  ];

  return (
    <div className="space-y-6 animate-fade-in pb-16">
      {/* Header Strip */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-hairline">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="font-display font-bold text-2xl text-ink tracking-tight">
              Cleared Assets Registry
            </h1>
            <span className="font-mono text-xs px-2.5 py-0.5 rounded-full bg-[#0E8F9C]/10 text-[#0E8F9C] border border-[#0E8F9C]/25 font-semibold">
              {totalItems} cleared by rules
            </span>
            {scanIdParam && (
              <span className="font-mono text-xs px-2.5 py-0.5 rounded-full bg-lens/10 text-lens border border-lens/20 font-semibold">
                Scan: {scanIdParam}
              </span>
            )}
          </div>
          <p className="text-xs text-ink-muted mt-1">
            Proves official brand assets and benign namesakes are automatically cleared by deterministic rules, preventing false-positive alert fatigue.
          </p>
        </div>

        {/* Back Link to Findings Queue */}
        <div className="flex items-center gap-3">
          <Link
            to={scanIdParam ? `/findings?scan_id=${scanIdParam}` : "/findings"}
            className="px-3.5 py-1.5 rounded-pill border border-hairline bg-surface hover:bg-surface-2 text-ink text-xs font-semibold transition-colors"
          >
            ← View Review Queue
          </Link>
        </div>
      </div>

      {/* Decision Tabs */}
      <div className="flex items-center gap-1 border-b border-hairline overflow-x-auto pb-px text-xs font-semibold">
        {decisionTabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => updateQuery({ decision: tab.id, page: "1" })}
            className={cn(
              "px-3.5 py-2 border-b-2 transition-colors whitespace-nowrap flex items-center gap-1.5",
              decisionParam === tab.id
                ? "border-[#0E8F9C] text-ink font-bold"
                : "border-transparent text-ink-muted hover:text-ink hover:border-hairline"
            )}
          >
            <span>{tab.label}</span>
            <span className="text-[10px] font-mono text-ink-muted font-normal">
              ({tab.ruleHint})
            </span>
          </button>
        ))}
      </div>

      {/* Filters Toolbar */}
      <div className="rounded-panel border border-hairline bg-surface p-4 shadow-sm space-y-3 text-xs">
        <div className="flex flex-wrap items-center gap-3">
          {/* Search Box */}
          <div className="relative min-w-[220px] flex-1">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-ink-muted" />
            <input
              type="text"
              value={queryParam}
              onChange={(e) => updateQuery({ q: e.target.value, page: "1" })}
              placeholder="Search cleared candidate name..."
              className="w-full pl-8 pr-3 py-1.5 rounded-panel-nested border border-hairline bg-surface-2 text-ink text-xs focus:outline-none focus:ring-1 focus:ring-lens"
            />
          </div>

          {/* Platform Filter */}
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

          {/* Reset Filters */}
          {(decisionParam !== "ALL" || platformParam !== "ALL" || queryParam !== "" || scanIdParam) && (
            <button
              onClick={() => {
                setSearchParams(new URLSearchParams(), { replace: true });
              }}
              className="text-[11px] text-ink-muted hover:text-ink underline ml-auto"
            >
              Reset filters
            </button>
          )}
        </div>
      </div>

      {/* Main Table */}
      <div className="rounded-panel border border-hairline bg-surface shadow-sm overflow-hidden">
        {isError ? (
          <div className="p-8 text-center space-y-2">
            <Info className="w-6 h-6 text-risk-critical mx-auto" />
            <h3 className="font-semibold text-xs text-ink">Failed to load cleared assets</h3>
            <p className="text-xs text-ink-muted">Please check API network connectivity.</p>
            <button
              onClick={() => refetch()}
              className="mt-2 px-3 py-1 rounded-pill bg-ink text-white text-xs font-semibold"
            >
              Retry
            </button>
          </div>
        ) : isLoading ? (
          <div className="p-6 space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div
                key={i}
                className="h-16 w-full rounded-panel-nested bg-surface-2 animate-pulse"
              />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="p-16 text-center space-y-2">
            <CheckCircle2 className="w-8 h-8 text-[#0E8F9C] mx-auto" />
            <h3 className="font-display font-semibold text-sm text-ink">
              No cleared assets match the filter criteria.
            </h3>
            <p className="text-xs text-ink-muted max-w-sm mx-auto">
              No candidates were cleared under the selected decision or platform filters.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-surface-2 text-ink-muted border-b border-hairline text-[11px] font-medium">
                  <th className="py-2.5 px-4 w-10">Icon</th>
                  <th className="py-2.5 px-4">Candidate Entity</th>
                  <th className="py-2.5 px-4">Platform</th>
                  <th className="py-2.5 px-4">Source</th>
                  <th className="py-2.5 px-4">Clearing Rule</th>
                  <th className="py-2.5 px-4">Matched Official Asset</th>
                  <th className="py-2.5 px-4 min-w-[280px]">Explanation</th>
                  <th className="py-2.5 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline">
                {items.map((item) => {
                  const isG4 = item.rule.startsWith("G4");
                  const isG5 = item.rule.startsWith("G5");
                  const isR2 = item.rule.startsWith("R2");
                  const hasCappedScore = (isG4 || isG5) && item.risk_score !== null;

                  return (
                    <tr
                      key={item.id}
                      className="hover:bg-surface-2/40 transition-colors"
                    >
                      {/* Icon */}
                      <td className="py-3 px-4">
                        <AssetIcon
                          src={item.candidate.icon_url || undefined}
                          alt={item.candidate.display_name}
                          size="sm"
                        />
                      </td>

                      {/* Candidate Name & Identifier */}
                      <td className="py-3 px-4">
                        <span className="font-semibold text-ink block leading-snug">
                          {item.candidate.display_name}
                        </span>
                        <span className="font-mono text-[11px] text-ink-muted block truncate max-w-[200px]">
                          {item.candidate.publisher_name || item.candidate.stable_identifier}
                        </span>
                      </td>

                      {/* Platform */}
                      <td className="py-3 px-4">
                        <span className="font-mono text-[11px] text-ink px-1.5 py-0.5 rounded bg-surface-2 border border-hairline">
                          {item.candidate.platform}
                        </span>
                      </td>

                      {/* Source */}
                      <td className="py-3 px-4">
                        <SourceBadge mode={item.source_mode || "LIVE"} />
                      </td>

                      {/* Rule ID (Mono) */}
                      <td className="py-3 px-4 whitespace-nowrap">
                        <div className="space-y-1">
                          <span className="font-mono text-[11px] font-semibold text-ink px-2 py-0.5 rounded bg-surface-2 border border-hairline block w-fit">
                            {item.rule}
                          </span>
                          <span className="font-mono text-[10px] text-[#0E8F9C] font-semibold block">
                            Decision: {item.decision}
                          </span>
                        </div>
                      </td>

                      {/* Matched Official Asset */}
                      <td className="py-3 px-4 whitespace-nowrap">
                        {item.matched_official_asset_id ? (
                          <Link
                            to="/brand"
                            className="inline-flex items-center gap-1 font-mono text-[11px] text-lens hover:underline"
                            title="Inspect registered official asset in Brand Profile"
                          >
                            <span>Official Asset</span>
                            <ExternalLink className="w-3 h-3" />
                          </Link>
                        ) : (
                          <span className="text-ink-muted text-[11px] italic">—</span>
                        )}
                      </td>

                      {/* Explanation with 15.3 rules */}
                      <td className="py-3 px-4">
                        <div className="space-y-1.5 max-w-md">
                          <p className="text-[11px] text-ink leading-relaxed">
                            {isR2
                              ? "Published by the registered developer. Consider registering this app."
                              : isG4
                              ? "Similar name, unrelated category, no corroborating evidence."
                              : isG5
                              ? "Declared unofficial in its bio. Not verified. Disclaimers can be copied by impersonators; an analyst may reopen this."
                              : item.explanation}
                          </p>

                          {/* G5 Badge: "Declared unofficial, not verified" */}
                          {isG5 && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-pill bg-amber-100 dark:bg-amber-950/40 text-amber-900 dark:text-amber-200 border border-amber-300 text-[10px] font-semibold">
                              Declared unofficial, not verified
                            </span>
                          )}

                          {/* Capped Score Note for G4/G5 */}
                          {hasCappedScore && (
                            <div className="flex items-center gap-1.5 text-[10px] font-mono text-ink-muted">
                              <span className="font-semibold text-ink">
                                Score: {item.risk_score}/100
                              </span>
                              <span>·</span>
                              <span className="text-amber-700 dark:text-amber-400 font-medium">
                                (score capped: G4/G5 prevents candidate reaching alert threshold)
                              </span>
                            </div>
                          )}
                        </div>
                      </td>

                      {/* Reopen Action (Reserved and disabled for P1) */}
                      <td className="py-3 px-4 text-right whitespace-nowrap">
                        <button
                          disabled
                          aria-disabled="true"
                          title="Reopening cleared items is a reserved P1 workflow (PATCH /cleared/{id}/reopen)"
                          className="opacity-45 cursor-not-allowed inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium rounded-pill bg-surface-2 border border-hairline text-ink-muted"
                        >
                          <RotateCcw className="w-3 h-3" />
                          <span>Reopen (P1)</span>
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Bar */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-hairline bg-surface-2 text-xs">
            <span className="text-ink-muted text-[11px]">
              Showing {offset + 1}–{Math.min(offset + limit, totalItems)} of {totalItems} cleared items
            </span>
            <div className="flex items-center gap-1">
              <button
                disabled={pageParam <= 1}
                onClick={() => updateQuery({ page: String(pageParam - 1) })}
                className="p-1 rounded hover:bg-surface border border-hairline disabled:opacity-40 disabled:cursor-not-allowed text-ink"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="px-2 font-mono text-[11px] text-ink font-semibold">
                Page {pageParam} of {totalPages}
              </span>
              <button
                disabled={pageParam >= totalPages}
                onClick={() => updateQuery({ page: String(pageParam + 1) })}
                className="p-1 rounded hover:bg-surface border border-hairline disabled:opacity-40 disabled:cursor-not-allowed text-ink"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
