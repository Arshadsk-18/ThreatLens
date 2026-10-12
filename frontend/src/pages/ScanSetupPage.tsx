import React, { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import { useBrand } from "@/context/useBrand";
import { ApiError } from "@/api/errors";
import type { Schema } from "@/api/client";
import { SourceBadge } from "@/components/cx/SourceBadge";
import {
  Play,
  RotateCw,
  AlertTriangle,
  Sparkles,
  Radio,
  ArrowRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

export function ScanSetupPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { activeBrand } = useBrand();

  // Mode: LIVE or DEMO
  const [mode, setMode] = useState<Schema["ScanMode"]>("DEMO");

  // Asset Types selection
  const [assetTypes, setAssetTypes] = useState<Schema["AssetType"][]>([
    "IOS_APP",
    "SOCIAL_ACCOUNT",
  ]);

  // Sources selection
  const [selectedSourceIds, setSelectedSourceIds] = useState<string[]>([
    "demo_fixtures",
    "recorded_fixtures",
  ]);

  // Scan Options
  const [queryLimit, setQueryLimit] = useState(25);
  const [includeIconSimilarity, setIncludeIconSimilarity] = useState(true);
  const [forceRefresh, setForceRefresh] = useState(false);
  const [allowStaleCache, setAllowStaleCache] = useState(false);

  // Errors / Conflicts
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorRequestId, setErrorRequestId] = useState<string | null>(null);
  const [runningScanId, setRunningScanId] = useState<string | null>(null);

  // Fetch sources status
  const { data: sourcesStatus, isLoading: sourcesLoading } = useQuery({
    queryKey: ["sources-status"],
    queryFn: () => apiClient.getSourcesStatus(),
  });

  // Fetch history scans for active brand
  const { data: scansData, isLoading: scansLoading } = useQuery({
    queryKey: ["scans", activeBrand?.id],
    queryFn: () => (activeBrand ? apiClient.getScans({ brand_id: activeBrand.id }) : null),
    enabled: !!activeBrand,
  });

  // Sync default sources when mode switches
  useEffect(() => {
    if (mode === "DEMO") {
      setSelectedSourceIds(["demo_fixtures", "recorded_fixtures"]);
    } else {
      // In LIVE mode, select connected live sources, never demo fixtures
      setSelectedSourceIds(["apple_itunes", "bluesky_public"]);
    }
    setErrorMessage(null);
    setErrorRequestId(null);
    setRunningScanId(null);
  }, [mode]);

  // Scan mutation
  const scanMutation = useMutation({
    mutationFn: async () => {
      if (!activeBrand) throw new Error("No active brand selected.");
      setErrorMessage(null);
      setErrorRequestId(null);
      setRunningScanId(null);

      // Prevent UI mixing demo fixtures on LIVE
      if (
        mode === "LIVE" &&
        selectedSourceIds.some((s) => s === "demo_fixtures" || s === "recorded_fixtures")
      ) {
        throw new ApiError(422, {
          code: "MODE_NOT_ALLOWED",
          message: "Demo fixtures cannot be selected in a LIVE scan.",
          request_id: "req-local-validation",
        });
      }

      return apiClient.createScan({
        brand_id: activeBrand.id,
        mode,
        asset_types: assetTypes,
        source_ids: selectedSourceIds,
        query_limit_per_source: Number(queryLimit),
        include_icon_similarity: includeIconSimilarity,
        force_refresh: forceRefresh,
        allow_stale_cache: allowStaleCache,
      });
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["scans"] });
      queryClient.invalidateQueries({ queryKey: ["brand-summary", activeBrand?.id] });
      navigate(`/scan/${data.id}`);
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError) {
        setErrorRequestId(err.requestId || null);
        if (err.status === 409 && err.code === "SCAN_ALREADY_RUNNING") {
          // Extract running scan id if provided in details
          const runningId = err.details?.find((d) => d.field === "scan_id")?.issue || null;
          setRunningScanId(runningId);
          setErrorMessage(
            err.message || "A scan is already in progress for this brand. Only one active scan is permitted at a time."
          );
          return;
        }

        if (err.status === 422 && err.code === "MODE_NOT_ALLOWED") {
          setErrorMessage(
            err.message || "MODE_NOT_ALLOWED: Mixing DEMO fixtures into a LIVE scan is strictly prohibited."
          );
          return;
        }

        setErrorMessage(err.message);
      } else {
        setErrorMessage("Failed to initiate scan. Please check your options and network connection.");
      }
    },
  });

  const toggleAssetType = (type: Schema["AssetType"]) => {
    if (assetTypes.includes(type)) {
      if (assetTypes.length > 1) {
        setAssetTypes(assetTypes.filter((t) => t !== type));
      }
    } else {
      setAssetTypes([...assetTypes, type]);
    }
  };

  const toggleSource = (sourceId: string) => {
    if (selectedSourceIds.includes(sourceId)) {
      if (selectedSourceIds.length > 1) {
        setSelectedSourceIds(selectedSourceIds.filter((id) => id !== sourceId));
      }
    } else {
      setSelectedSourceIds([...selectedSourceIds, sourceId]);
    }
  };

  const scansList = scansData?.items || [];

  return (
    <div className="space-y-8 animate-fade-in pb-16">
      {/* Header */}
      <div className="pb-4 border-b border-hairline">
        <h1 className="font-display font-bold text-2xl text-ink tracking-tight">
          Scan Setup & History
        </h1>
        <p className="text-xs text-ink-muted mt-1">
          Target brand: <strong className="text-ink">{activeBrand?.name || "Kaveri Bank"}</strong>.
          Configure discovery scope, provider source selection, and run history.
        </p>
      </div>

      {/* Mode Choice: LIVE vs DEMO Cards */}
      <div className="space-y-3">
        <label className="text-xs font-semibold text-ink uppercase tracking-wider block">
          1. Select Scan Execution Mode
        </label>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* DEMO Card */}
          <div
            onClick={() => setMode("DEMO")}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && setMode("DEMO")}
            className={cn(
              "p-5 rounded-panel border transition-all text-left cursor-pointer relative",
              mode === "DEMO"
                ? "bg-surface border-lens shadow-sm ring-2 ring-lens/20"
                : "bg-surface-2 border-hairline hover:border-hairline/80 opacity-80 hover:opacity-100"
            )}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-lens" />
                <span className="font-display font-bold text-sm text-ink">DEMO Mode</span>
              </div>
              <SourceBadge status="SIMULATED" />
            </div>
            <p className="text-xs text-ink-muted leading-relaxed">
              Uses local fixtures and recorded responses. Never calls external platform APIs. All candidate records are clearly badged as simulated or cached.
            </p>
            <div className="mt-3 pt-3 border-t border-hairline/60 flex items-center gap-2 text-[11px] text-ink-muted">
              <Sparkles className="w-3.5 h-3.5 text-lens shrink-0" />
              <span>Offline deterministic verification & evaluation fixtures.</span>
            </div>
          </div>

          {/* LIVE Card */}
          <div
            onClick={() => setMode("LIVE")}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && setMode("LIVE")}
            className={cn(
              "p-5 rounded-panel border transition-all text-left cursor-pointer relative",
              mode === "LIVE"
                ? "bg-surface border-lens shadow-sm ring-2 ring-lens/20"
                : "bg-surface-2 border-hairline hover:border-hairline/80 opacity-80 hover:opacity-100"
            )}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#0E8F9C]" />
                <span className="font-display font-bold text-sm text-ink">LIVE Mode</span>
              </div>
              <SourceBadge status="LIVE" />
            </div>
            <p className="text-xs text-ink-muted leading-relaxed">
              Directly queries live provider endpoints. Response cache is permitted and labelled with timestamps. Apple catalog limited to ~20 requests/minute.
            </p>
            <div className="mt-3 pt-3 border-t border-hairline/60 flex items-center gap-2 text-[11px] text-ink-muted">
              <Radio className="w-3.5 h-3.5 text-[#0E8F9C] shrink-0" />
              <span>Real-time discovery on Apple iTunes & Bluesky public actors.</span>
            </div>
          </div>
        </div>
      </div>

      {/* Asset Types & Sources Grid */}
      <div className="rounded-panel border border-hairline bg-surface p-6 shadow-sm space-y-6">
        {/* Asset Types */}
        <div>
          <label className="text-xs font-semibold text-ink uppercase tracking-wider block mb-2">
            2. Target Asset Types
          </label>
          <div className="flex flex-wrap gap-2.5">
            {[
              { id: "IOS_APP" as Schema["AssetType"], label: "iOS Applications", desc: "Apple App Store" },
              { id: "SOCIAL_ACCOUNT" as Schema["AssetType"], label: "Social Accounts", desc: "Bluesky Public Directory" },
              { id: "ANDROID_APP" as Schema["AssetType"], label: "Android Apps", desc: "Google Play (Catalog Snapshot)" },
            ].map((type) => {
              const active = assetTypes.includes(type.id);
              return (
                <button
                  key={type.id}
                  type="button"
                  onClick={() => toggleAssetType(type.id)}
                  className={cn(
                    "px-3.5 py-2 rounded-panel-nested border text-xs text-left transition-colors flex items-center gap-2.5",
                    active
                      ? "bg-surface border-lens text-ink font-semibold shadow-xs"
                      : "bg-surface-2 border-hairline text-ink-muted hover:border-hairline/80"
                  )}
                >
                  <input
                    type="checkbox"
                    checked={active}
                    readOnly
                    className="w-3.5 h-3.5 rounded text-lens pointer-events-none"
                  />
                  <div>
                    <span className="block leading-none">{type.label}</span>
                    <span className="text-[10px] text-ink-muted block mt-0.5">{type.desc}</span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Sources Selection */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs font-semibold text-ink uppercase tracking-wider block">
              3. Connected Provider Sources
            </label>
            <span className="text-[11px] text-ink-muted">
              Built from live <code className="font-mono text-ink">GET /sources/status</code>
            </span>
          </div>

          {sourcesLoading ? (
            <div className="p-4 text-xs text-ink-muted">Loading connector statuses...</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {sourcesStatus?.map((source) => {
                const isNotConnected = source.status === "NOT_CONNECTED";
                const isFixtureSource =
                  source.source_id === "demo_fixtures" ||
                  source.source_id === "recorded_fixtures";
                const isDemoOnlyLocked = mode === "LIVE" && isFixtureSource;
                const isChecked = selectedSourceIds.includes(source.source_id);
                const isDisabled = isNotConnected || isDemoOnlyLocked;

                return (
                  <div
                    key={source.source_id}
                    className={cn(
                      "p-3.5 rounded-panel-nested border text-xs transition-colors relative flex flex-col justify-between",
                      isDisabled
                        ? "bg-surface-2/60 border-hairline/60 opacity-60 cursor-not-allowed"
                        : isChecked
                        ? "bg-surface border-lens shadow-xs cursor-pointer"
                        : "bg-surface-2 border-hairline hover:border-hairline/80 cursor-pointer"
                    )}
                    onClick={() => {
                      if (!isDisabled) {
                        toggleSource(source.source_id);
                      }
                    }}
                  >
                    <div>
                      <div className="flex items-start justify-between gap-2 mb-1.5">
                        <div className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={isChecked}
                            disabled={isDisabled}
                            onChange={() => {}}
                            className="w-3.5 h-3.5 rounded text-lens pointer-events-none"
                          />
                          <span className="font-semibold text-ink block">{source.display_name}</span>
                        </div>
                        <SourceBadge status={source.status} />
                      </div>

                      {/* Not Connected Contract Copy */}
                      {isNotConnected && (
                        <p className="text-[11px] text-risk-critical/90 font-medium mt-1 leading-snug">
                          {source.display_name}: not connected. {source.message || "Requires platform API access."} Not queried.
                        </p>
                      )}

                      {/* Demo Only Locked Notice */}
                      {isDemoOnlyLocked && (
                        <p className="text-[11px] text-amber-700 font-medium mt-1 leading-snug">
                          DEMO mode only. Cannot be mixed with LIVE provider scans.
                        </p>
                      )}

                      {!isNotConnected && !isDemoOnlyLocked && (
                        <p className="text-[11px] text-ink-muted mt-1 leading-snug">
                          {source.message}
                          {source.rate_limit_note && (
                            <span className="block text-[10px] font-mono text-ink-muted mt-0.5">
                              Rate limit: {source.rate_limit_note}
                            </span>
                          )}
                        </p>
                      )}
                    </div>

                    <div className="pt-2 mt-2 border-t border-hairline/60 flex items-center justify-between text-[10px] font-mono text-ink-muted">
                      <span>{source.platform}</span>
                      <span>{source.source_id}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Options & Configuration */}
        <div className="pt-4 border-t border-hairline space-y-4">
          <label className="text-xs font-semibold text-ink uppercase tracking-wider block">
            4. Query & Caching Parameters
          </label>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Query Limit */}
            <div className="p-3.5 rounded-panel-nested border border-hairline bg-surface-2 space-y-1.5">
              <div className="flex items-center justify-between">
                <label htmlFor="query-limit-input" className="text-xs font-semibold text-ink">
                  Query Limit per Source: <span className="font-mono text-lens">{queryLimit}</span>
                </label>
                <span className="text-[10px] text-ink-muted">Max: 50</span>
              </div>
              <input
                id="query-limit-input"
                type="range"
                min={5}
                max={50}
                step={5}
                value={queryLimit}
                onChange={(e) => setQueryLimit(Number(e.target.value))}
                className="w-full accent-lens cursor-pointer"
              />
              <p className="text-[11px] text-ink-muted leading-tight">
                Controls maximum recall depth per planned search query term. Default is 25.
              </p>
            </div>

            {/* Icon Similarity */}
            <label className="p-3.5 rounded-panel-nested border border-hairline bg-surface-2 flex items-start gap-2.5 cursor-pointer hover:border-hairline/80 transition-colors">
              <input
                type="checkbox"
                checked={includeIconSimilarity}
                onChange={(e) => setIncludeIconSimilarity(e.target.checked)}
                className="w-4 h-4 rounded text-lens mt-0.5"
              />
              <div className="text-xs">
                <span className="font-semibold text-ink block">Include Icon / Avatar Similarity</span>
                <span className="text-[11px] text-ink-muted block mt-0.5 leading-snug">
                  Computes perceptual pHash comparisons against registered official app icons and profile avatars.
                </span>
              </div>
            </label>

            {/* Force Refresh */}
            <label className="p-3.5 rounded-panel-nested border border-hairline bg-surface-2 flex items-start gap-2.5 cursor-pointer hover:border-hairline/80 transition-colors">
              <input
                type="checkbox"
                checked={forceRefresh}
                onChange={(e) => setForceRefresh(e.target.checked)}
                className="w-4 h-4 rounded text-lens mt-0.5"
              />
              <div className="text-xs">
                <span className="font-semibold text-ink block">Force Refresh (Bypass Cache)</span>
                <span className="text-[11px] text-ink-muted block mt-0.5 leading-snug">
                  Forces fresh live requests to providers instead of reading from TTL response cache.
                </span>
              </div>
            </label>

            {/* Allow Stale Cache (Section 5.3 explanation) */}
            <label className="p-3.5 rounded-panel-nested border border-hairline bg-surface-2 flex items-start gap-2.5 cursor-pointer hover:border-hairline/80 transition-colors">
              <input
                type="checkbox"
                checked={allowStaleCache}
                onChange={(e) => setAllowStaleCache(e.target.checked)}
                className="w-4 h-4 rounded text-lens mt-0.5"
              />
              <div className="text-xs">
                <span className="font-semibold text-ink block">Allow Stale Cache (Section 5.3)</span>
                <span className="text-[11px] text-ink-muted block mt-0.5 leading-snug">
                  If a provider fails and allow_stale_cache is enabled, stale cache may be used, outcome status is PARTIAL, and message states the cache time. Default false.
                </span>
              </div>
            </label>
          </div>
        </div>

        {/* Error / Conflict Feedback */}
        {errorMessage && (
          <div className="p-4 rounded-panel-nested bg-risk-critical/10 border border-risk-critical/30 text-risk-critical text-xs space-y-2">
            <div className="flex items-center gap-2 font-semibold">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{errorMessage}</span>
            </div>
            {errorRequestId && (
              <span className="font-mono text-[10px] pl-6 block opacity-80">
                Request ID: {errorRequestId}
              </span>
            )}
            {runningScanId && (
              <div className="pl-6">
                <Link
                  to={`/scan/${runningScanId}`}
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-pill bg-risk-critical text-white font-semibold hover:bg-risk-critical/90 transition-colors text-xs"
                >
                  <span>Open Active Scan ({runningScanId})</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            )}
          </div>
        )}

        {/* Launch Button */}
        <div className="flex justify-end pt-2">
          <button
            type="button"
            onClick={() => scanMutation.mutate()}
            disabled={scanMutation.isPending || selectedSourceIds.length === 0}
            className={cn(
              "px-6 py-2.5 text-xs font-semibold text-white bg-ink rounded-pill shadow-sm flex items-center gap-2 hover:bg-ink/90 transition-all",
              (scanMutation.isPending || selectedSourceIds.length === 0) &&
                "opacity-50 cursor-not-allowed"
            )}
          >
            {scanMutation.isPending ? (
              <RotateCw className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4 fill-current" />
            )}
            <span>
              {scanMutation.isPending ? "Orchestrating Scan..." : `Launch ${mode} Scan`}
            </span>
          </button>
        </div>
      </div>

      {/* Historical Scans Section */}
      <div className="rounded-panel border border-hairline bg-surface shadow-sm overflow-hidden">
        <div className="p-6 border-b border-hairline flex items-center justify-between">
          <div>
            <h2 className="font-display font-semibold text-base text-ink tracking-tight">
              Scan Execution History
            </h2>
            <p className="text-xs text-ink-muted mt-0.5">
              Chronological log of discovery runs for {activeBrand?.name}.
            </p>
          </div>
          <span className="text-xs font-mono text-ink-muted">
            {scansList.length} recorded run(s)
          </span>
        </div>

        {scansLoading ? (
          <div className="p-8 text-center text-xs text-ink-muted">Loading scan history...</div>
        ) : scansList.length === 0 ? (
          <div className="p-10 text-center space-y-1">
            <p className="text-xs font-semibold text-ink">No historical scans recorded</p>
            <p className="text-xs text-ink-muted">Launch your first scan above to review candidates.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-surface-2 text-ink-muted border-b border-hairline text-[11px] font-medium">
                  <th className="py-2.5 px-4 font-mono">Scan ID</th>
                  <th className="py-2.5 px-4">Mode</th>
                  <th className="py-2.5 px-4">Status</th>
                  <th className="py-2.5 px-4">Stage & Progress</th>
                  <th className="py-2.5 px-4 text-center">Findings</th>
                  <th className="py-2.5 px-4 text-center">Cleared</th>
                  <th className="py-2.5 px-4">Created</th>
                  <th className="py-2.5 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline">
                {scansList.map((s) => (
                  <tr key={s.id} className="hover:bg-surface-2/40 transition-colors">
                    <td className="py-3 px-4">
                      <Link
                        to={`/scan/${s.id}`}
                        className="font-mono text-xs font-semibold text-lens hover:underline"
                      >
                        {s.id}
                      </Link>
                    </td>
                    <td className="py-3 px-4">
                      <SourceBadge status={s.mode === "DEMO" ? "SIMULATED" : "LIVE"} />
                    </td>
                    <td className="py-3 px-4">
                      <SourceBadge status={s.status} />
                    </td>
                    <td className="py-3 px-4">
                      <span className="font-mono text-[11px] text-ink">{s.stage}</span>
                      <span className="text-[10px] text-ink-muted ml-1.5">({s.progress_percent}%)</span>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className="font-mono font-semibold text-ink">
                        {s.findings_count}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className="font-mono text-ink-muted">
                        {s.cleared_count}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className="text-[11px] text-ink-muted">
                        {new Date(s.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Link
                        to={`/scan/${s.id}`}
                        className="inline-flex items-center gap-1 px-3 py-1 text-xs font-medium text-lens hover:bg-lens/5 rounded-pill border border-lens/30 transition-colors"
                      >
                        <span>View</span>
                        <ArrowRight className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
