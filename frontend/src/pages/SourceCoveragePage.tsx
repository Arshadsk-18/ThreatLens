import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import { ApiError } from "@/api/errors";
import {
  RefreshCw,
  AlertTriangle,
  Info,
} from "lucide-react";
import { cn } from "@/lib/utils";

export function SourceCoveragePage() {
  const queryClient = useQueryClient();
  const [rateLimitNotice, setRateLimitNotice] = useState<string | null>(null);

  const {
    data: sources,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["sources-status"],
    queryFn: () => apiClient.getSourcesStatus(),
  });

  // "Check now" mutation with refresh=true
  const checkNowMutation = useMutation({
    mutationFn: async () => {
      setRateLimitNotice(null);
      return apiClient.getSourcesStatus(true);
    },
    onSuccess: (data) => {
      queryClient.setQueryData(["sources-status"], data);
      const rateLimitedSource = data.find((s) => s.status === "RATE_LIMITED");
      if (rateLimitedSource) {
        setRateLimitNotice(
          `Provider '${rateLimitedSource.display_name}' reported rate limiting. Rate limit note: ${rateLimitedSource.rate_limit_note || "Throttled by remote platform"}.`
        );
      }
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError && err.status === 429) {
        setRateLimitNotice("Rate limit exceeded on refresh check. Please wait before retrying.");
      } else {
        setRateLimitNotice("Unable to refresh live provider status. Reverted to cached health.");
      }
    },
  });

  const sourceItems = sources || [];
  const connectedCount = sourceItems.filter((s) => s.status === "CONNECTED").length;

  return (
    <div className="space-y-6 animate-fade-in pb-16">
      {/* Header Strip */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-hairline">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="font-display font-bold text-2xl text-ink tracking-tight">
              Source Coverage & Provider Health
            </h1>
            <span className="font-mono text-xs px-2.5 py-0.5 rounded-full bg-[#0E8F9C]/10 text-[#0E8F9C] border border-[#0E8F9C]/25 font-semibold">
              {connectedCount} / {sourceItems.length} Connected
            </span>
          </div>
          <p className="text-xs text-ink-muted mt-1">
            Real-time catalog search connectivity, supported query execution modes, and platform rate limits (§11.1).
          </p>
        </div>

        {/* Action: Check Now Button */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => checkNowMutation.mutate()}
            disabled={checkNowMutation.isPending || isLoading}
            className={cn(
              "px-4 py-2 text-xs font-semibold rounded-pill bg-ink text-white hover:bg-ink/90 flex items-center gap-2 transition-all shadow-sm",
              (checkNowMutation.isPending || isLoading) && "opacity-60 cursor-not-allowed"
            )}
            title="Perform active health check (GET /sources/status?refresh=true)"
          >
            <RefreshCw
              className={cn("w-3.5 h-3.5", checkNowMutation.isPending && "animate-spin")}
            />
            <span>{checkNowMutation.isPending ? "Checking sources..." : "Check now"}</span>
          </button>
        </div>
      </div>

      {/* Rate Limit Banner if triggered */}
      {rateLimitNotice && (
        <div className="p-3.5 rounded-panel bg-amber-500/10 border border-amber-500/30 text-amber-900 dark:text-amber-200 text-xs flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 text-amber-600" />
            <span>{rateLimitNotice}</span>
          </div>
          <button
            onClick={() => setRateLimitNotice(null)}
            className="text-[11px] underline font-medium hover:text-ink shrink-0"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Legend Card per Requirement */}
      <div className="rounded-panel border border-hairline bg-surface p-4 shadow-sm space-y-3">
        <div className="flex items-center gap-2 text-xs font-semibold text-ink">
          <Info className="w-4 h-4 text-lens" />
          <span>Source Modes & Status Legend</span>
        </div>
        <p className="text-xs text-ink-muted leading-relaxed">
          ThreatLens surfaces provider health honestly. Status reflects the last real outcome. Unconnected sources are not errored; they are simply not queried.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-3 pt-1 text-xs">
          <div className="p-2.5 rounded-panel-nested bg-surface-2 border border-hairline space-y-1">
            <div className="flex items-center gap-1.5 font-semibold text-teal-700 dark:text-teal-400">
              <span className="w-2 h-2 rounded-full bg-teal-500" />
              <span>LIVE</span>
            </div>
            <p className="text-[11px] text-ink-muted leading-tight">
              Real-time query sent directly to platform catalog APIs.
            </p>
          </div>

          <div className="p-2.5 rounded-panel-nested bg-surface-2 border border-hairline space-y-1">
            <div className="flex items-center gap-1.5 font-semibold text-lens">
              <span className="w-2 h-2 rounded-full bg-lens" />
              <span>CACHED</span>
            </div>
            <p className="text-[11px] text-ink-muted leading-tight">
              Replay from stored response snapshot when live limits apply.
            </p>
          </div>

          <div className="p-2.5 rounded-panel-nested bg-surface-2 border border-hairline space-y-1">
            <div className="flex items-center gap-1.5 font-semibold text-blue-700 dark:text-blue-400">
              <span className="w-2 h-2 rounded-full bg-blue-500" />
              <span>SIMULATED</span>
            </div>
            <p className="text-[11px] text-ink-muted leading-tight">
              Synthetic benchmark fixtures for offline test evaluation.
            </p>
          </div>

          <div className="p-2.5 rounded-panel-nested bg-surface-2 border border-hairline space-y-1">
            <div className="flex items-center gap-1.5 font-semibold text-ink-muted">
              <span className="w-2 h-2 rounded-full bg-hairline" />
              <span>NOT_CONNECTED</span>
            </div>
            <p className="text-[11px] text-ink-muted leading-tight">
              No API access configured; provider is not queried.
            </p>
          </div>

          <div className="p-2.5 rounded-panel-nested bg-surface-2 border border-hairline space-y-1">
            <div className="flex items-center gap-1.5 font-semibold text-amber-700 dark:text-amber-400">
              <span className="w-2 h-2 rounded-full bg-amber-500" />
              <span>RATE_LIMITED / ERROR</span>
            </div>
            <p className="text-[11px] text-ink-muted leading-tight">
              Provider throttled queries or reported connection issues.
            </p>
          </div>
        </div>
      </div>

      {/* Grid of Sources */}
      {isError ? (
        <div className="p-8 text-center rounded-panel bg-surface border border-hairline space-y-2">
          <AlertTriangle className="w-6 h-6 text-risk-critical mx-auto" />
          <h3 className="font-semibold text-xs text-ink">Failed to retrieve sources</h3>
          <p className="text-xs text-ink-muted">
            {error instanceof ApiError ? error.message : "Error contacting /sources/status."}
          </p>
          {error instanceof ApiError && error.requestId && (
            <span className="font-mono text-[10px] text-ink-muted block">
              Request ID: {error.requestId}
            </span>
          )}
          <button
            onClick={() => refetch()}
            className="mt-2 px-3 py-1.5 rounded-pill bg-ink text-white text-xs font-semibold hover:bg-ink/90 transition-colors"
          >
            Retry
          </button>
        </div>
      ) : isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div
              key={i}
              className="h-44 rounded-panel bg-surface border border-hairline animate-pulse"
            />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sourceItems.map((src) => {
            const isConnected = src.status === "CONNECTED";
            const isNotConnected = src.status === "NOT_CONNECTED";
            const isRateLimited = src.status === "RATE_LIMITED";

            return (
              <div
                key={src.source_id}
                className={cn(
                  "p-4 rounded-panel border bg-surface shadow-xs space-y-3 transition-all flex flex-col justify-between",
                  isConnected ? "border-hairline" : "border-hairline/70 bg-surface-2/40"
                )}
              >
                {/* Source Header */}
                <div className="space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h3 className="font-display font-semibold text-sm text-ink leading-tight">
                        {src.display_name}
                      </h3>
                      <span className="font-mono text-[11px] text-ink-muted block mt-0.5">
                        {src.source_id}
                      </span>
                    </div>
                    {/* Status Pill */}
                    <span
                      className={cn(
                        "px-2.5 py-0.5 rounded-pill text-[10px] font-semibold border shrink-0 uppercase font-mono",
                        isConnected && "bg-teal-500/10 text-teal-700 dark:text-teal-400 border-teal-500/30",
                        isNotConnected && "bg-surface-2 text-ink-muted border-hairline",
                        isRateLimited && "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/30",
                        src.status === "PARTIAL" && "bg-blue-500/10 text-blue-700 border-blue-500/30",
                        src.status === "ERROR" && "bg-risk-critical/10 text-risk-critical border-risk-critical/30"
                      )}
                    >
                      {src.status.replace(/_/g, " ")}
                    </span>
                  </div>

                  {/* Platform & Asset Types */}
                  <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
                    <span className="font-mono px-2 py-0.5 rounded bg-surface-2 border border-hairline text-ink">
                      {src.platform}
                    </span>
                    {src.asset_types.map((at) => (
                      <span
                        key={at}
                        className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-surface border border-hairline text-ink-muted"
                      >
                        {at}
                      </span>
                    ))}
                  </div>

                  {/* Message (verbatim from contract) */}
                  <p className="text-xs text-ink leading-relaxed pt-1">
                    {src.message}
                  </p>
                </div>

                {/* Footer attributes */}
                <div className="pt-2 border-t border-hairline/80 space-y-2 text-[11px]">
                  {/* Supported Modes & Default Mode */}
                  <div className="flex items-center justify-between">
                    <span className="text-ink-muted">Supported Modes:</span>
                    <div className="flex items-center gap-1">
                      {src.supported_modes.map((mode) => (
                        <span
                          key={mode}
                          className={cn(
                            "px-1.5 py-0.2 rounded text-[10px] font-mono font-medium",
                            mode === src.default_mode
                              ? "bg-ink text-white font-bold"
                              : "bg-surface-2 text-ink-muted border border-hairline"
                          )}
                          title={mode === src.default_mode ? "Default mode" : undefined}
                        >
                          {mode}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Rate Limit Note */}
                  {src.rate_limit_note && (
                    <div className="flex items-center justify-between text-ink-muted">
                      <span>Rate limit note:</span>
                      <span className="font-mono text-[10px] text-ink truncate max-w-[170px]" title={src.rate_limit_note}>
                        {src.rate_limit_note}
                      </span>
                    </div>
                  )}

                  {/* Last Checked At */}
                  <div className="flex items-center justify-between text-ink-muted">
                    <span>Last checked:</span>
                    <span className="font-mono text-[10px] text-ink">
                      {src.last_checked_at
                        ? new Date(src.last_checked_at).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                            second: "2-digit",
                          })
                        : "Never"}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
