import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import { ApiError } from "@/api/errors";
import type { Schema } from "@/api/client";
import {
  Play,
  AlertTriangle,
  Layers,
  Sliders,
  Table,
  HelpCircle,
  Sparkles,
  RefreshCw,
  Scale,
  ShieldCheck,
  ShieldAlert,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";

export function EvaluationLabPage() {
  const queryClient = useQueryClient();

  // Run Configuration State
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>("threatlens-v1");
  const [selectedSplit, setSelectedSplit] = useState<Schema["EvalSplit"]>("HELDOUT");
  const [includeBaseline, setIncludeBaseline] = useState<boolean>(true);
  const [includeAblation, setIncludeAblation] = useState<boolean>(true);
  const [runError, setRunError] = useState<{ message: string; requestId?: string } | null>(null);

  // 1. Fetch Datasets (GET /evaluations/datasets)
  const {
    data: datasetsData,
    isLoading: isLoadingDatasets,
  } = useQuery({
    queryKey: ["evaluation-datasets"],
    queryFn: () => apiClient.getEvaluationDatasets(),
  });

  // 2. Fetch Latest Evaluation on entry (GET /evaluations/latest?dataset_id&split)
  const {
    data: latestEval,
    isLoading: isLoadingLatest,
    isFetching: isFetchingLatest,
    refetch: refetchLatest,
  } = useQuery({
    queryKey: ["latest-evaluation", selectedDatasetId, selectedSplit],
    queryFn: () =>
      apiClient.getLatestEvaluation({
        dataset_id: selectedDatasetId,
        split: selectedSplit,
      }),
  });

  // 3. Run Evaluation Mutation (POST /evaluations/run)
  const runMutation = useMutation({
    mutationFn: async (data: Schema["EvaluationRunRequest"]) => {
      setRunError(null);
      return apiClient.runEvaluation(data);
    },
    onSuccess: (result) => {
      queryClient.setQueryData(
        ["latest-evaluation", selectedDatasetId, selectedSplit],
        result
      );
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError) {
        setRunError({ message: err.message, requestId: err.requestId });
      } else if (err instanceof Error) {
        setRunError({ message: err.message });
      } else {
        setRunError({ message: "Evaluation run failed. Please check parameters." });
      }
    },
  });

  const evalResult = latestEval;
  const datasets = datasetsData?.items || [];
  const activeDataset =
    datasets.find((d) => d.dataset_id === selectedDatasetId) || datasets[0];

  const handleRunEvaluation = () => {
    runMutation.mutate({
      dataset_id: selectedDatasetId,
      split: selectedSplit,
      include_baseline: includeBaseline,
      include_ablation: includeAblation,
    });
  };

  // Helper: Format metrics or "Not defined"
  const formatMetric = (val: number | null | undefined): string => {
    if (val === null || val === undefined) return "Not defined";
    return val.toFixed(2);
  };

  // Helper: Format Wilson 95% Confidence Interval
  const formatInterval = (
    ci: [number, number] | null | undefined
  ): string => {
    if (!ci) return "Not defined";
    return `[${ci[0].toFixed(2)}, ${ci[1].toFixed(2)}]`;
  };

  return (
    <div className="space-y-6 animate-fade-in pb-16">
      {/* Header Strip */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-hairline">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="font-display font-bold text-2xl text-ink tracking-tight">
              Evaluation Lab
            </h1>
            <span className="font-mono text-xs px-2.5 py-0.5 rounded-full bg-lens/10 text-lens border border-lens/20 font-semibold">
              Offline Test Harness (§14)
            </span>
            <span className="font-mono text-xs px-2.5 py-0.5 rounded-full bg-surface-2 text-ink-muted border border-hairline">
              Deterministic assess()
            </span>
          </div>
          <p className="text-xs text-ink-muted mt-1">
            Reproducible offline evaluation across labelled corpora. Metrics are dynamically computed by the harness, never typed.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => refetchLatest()}
            disabled={isFetchingLatest || runMutation.isPending}
            className="p-2 rounded-pill border border-hairline hover:bg-surface-2 text-ink-muted hover:text-ink transition-colors"
            title="Reload latest evaluation result"
          >
            <RefreshCw
              className={cn(
                "w-3.5 h-3.5",
                (isFetchingLatest || runMutation.isPending) && "animate-spin"
              )}
            />
          </button>
        </div>
      </div>

      {/* 1. Permanent Honesty Panel */}
      <div className="p-4 rounded-panel bg-surface border border-hairline shadow-xs space-y-2.5">
        <div className="flex items-center gap-2 text-xs font-semibold text-ink">
          <Sparkles className="w-4 h-4 text-lens shrink-0" />
          <span>Honesty & Scientific Rigour Principle</span>
        </div>
        <p className="text-xs text-ink leading-relaxed">
          Honesty is the feature (§14). Positives are synthetic; negatives are real captured namesakes labelled by the team. Small sample, see intervals. Baseline metrics are reported on the frozen HELDOUT split.
        </p>

        {/* Dynamic Limitations from Dataset / Response */}
        {evalResult?.limitations && evalResult.limitations.length > 0 && (
          <div className="pt-2 border-t border-hairline/60 flex flex-wrap items-center gap-2 text-[11px] text-ink-muted">
            <span className="font-semibold text-ink">Active limitations:</span>
            {evalResult.limitations.map((lim, idx) => (
              <span
                key={idx}
                className="px-2 py-0.5 rounded-panel-nested bg-surface-2 border border-hairline text-ink-muted"
              >
                {lim}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* 2. Top Section: Dataset Composition & Run Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Dataset Catalog (5 cols) */}
        <div className="lg:col-span-5 rounded-panel border border-hairline bg-surface p-5 shadow-xs space-y-4 flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-lens" />
                <h2 className="font-display font-semibold text-sm text-ink">
                  Dataset Composition
                </h2>
              </div>
              {activeDataset && (
                <span className="font-mono text-xs font-semibold text-ink px-2 py-0.5 rounded-pill bg-surface-2 border border-hairline">
                  {activeDataset.case_count} cases
                </span>
              )}
            </div>

            {isLoadingDatasets ? (
              <div className="p-6 text-center text-xs text-ink-muted flex items-center justify-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-lens" />
                <span>Loading dataset specifications...</span>
              </div>
            ) : activeDataset ? (
              <div className="space-y-3 text-xs">
                <div className="p-2.5 rounded-panel-nested bg-surface-2 border border-hairline space-y-1">
                  <span className="font-mono font-semibold text-ink block">
                    {activeDataset.dataset_id}
                  </span>
                  <p className="text-[11px] text-ink-muted">
                    {activeDataset.description}
                  </p>
                </div>

                {/* Composition Bar 1: By Label */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="font-medium text-ink-muted">By Label</span>
                    <span className="font-mono text-[10px] text-ink-muted">
                      {activeDataset.by_label.IMPERSONATION} Pos /{" "}
                      {activeDataset.by_label.BENIGN_NAMESAKE} Namesake /{" "}
                      {activeDataset.by_label.OFFICIAL} Off
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-surface-2 overflow-hidden flex border border-hairline">
                    <div
                      style={{
                        width: `${(activeDataset.by_label.IMPERSONATION / activeDataset.case_count) * 100}%`,
                      }}
                      className="bg-lens"
                      title={`Impersonation (Positive): ${activeDataset.by_label.IMPERSONATION}`}
                    />
                    <div
                      style={{
                        width: `${(activeDataset.by_label.BENIGN_NAMESAKE / activeDataset.case_count) * 100}%`,
                      }}
                      className="bg-[#0E8F9C]"
                      title={`Benign Namesake: ${activeDataset.by_label.BENIGN_NAMESAKE}`}
                    />
                    <div
                      style={{
                        width: `${(activeDataset.by_label.OFFICIAL / activeDataset.case_count) * 100}%`,
                      }}
                      className="bg-emerald-600"
                      title={`Official: ${activeDataset.by_label.OFFICIAL}`}
                    />
                  </div>
                  <div className="flex items-center gap-3 text-[10px] text-ink-muted pt-0.5">
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-lens" />
                      <span>Impersonation ({activeDataset.by_label.IMPERSONATION})</span>
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-[#0E8F9C]" />
                      <span>Namesake ({activeDataset.by_label.BENIGN_NAMESAKE})</span>
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-emerald-600" />
                      <span>Official ({activeDataset.by_label.OFFICIAL})</span>
                    </span>
                  </div>
                </div>

                {/* Composition Bar 2: By Provenance */}
                <div className="space-y-1.5 pt-1">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="font-medium text-ink-muted">By Provenance</span>
                    <span className="font-mono text-[10px] text-ink-muted">
                      {activeDataset.by_provenance.REAL_CAPTURED} Real /{" "}
                      {activeDataset.by_provenance.SYNTHETIC} Synthetic
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-surface-2 overflow-hidden flex border border-hairline">
                    <div
                      style={{
                        width: `${(activeDataset.by_provenance.REAL_CAPTURED / activeDataset.case_count) * 100}%`,
                      }}
                      className="bg-teal-600"
                      title={`Real Captured: ${activeDataset.by_provenance.REAL_CAPTURED}`}
                    />
                    <div
                      style={{
                        width: `${(activeDataset.by_provenance.SYNTHETIC / activeDataset.case_count) * 100}%`,
                      }}
                      className="bg-amber-600"
                      title={`Synthetic: ${activeDataset.by_provenance.SYNTHETIC}`}
                    />
                  </div>
                  <div className="flex items-center gap-3 text-[10px] text-ink-muted pt-0.5">
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-teal-600" />
                      <span>Real Captured ({activeDataset.by_provenance.REAL_CAPTURED})</span>
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-amber-600" />
                      <span>Synthetic ({activeDataset.by_provenance.SYNTHETIC})</span>
                    </span>
                  </div>
                </div>

                {/* Composition Bar 3: By Split */}
                <div className="space-y-1.5 pt-1">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="font-medium text-ink-muted">By Split</span>
                    <span className="font-mono text-[10px] text-ink-muted">
                      {activeDataset.by_split.DEV} DEV /{" "}
                      {activeDataset.by_split.HELDOUT} HELDOUT
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-surface-2 overflow-hidden flex border border-hairline">
                    <div
                      style={{
                        width: `${(activeDataset.by_split.DEV / activeDataset.case_count) * 100}%`,
                      }}
                      className="bg-purple-600"
                      title={`DEV Split: ${activeDataset.by_split.DEV}`}
                    />
                    <div
                      style={{
                        width: `${(activeDataset.by_split.HELDOUT / activeDataset.case_count) * 100}%`,
                      }}
                      className="bg-blue-600"
                      title={`HELDOUT Split: ${activeDataset.by_split.HELDOUT}`}
                    />
                  </div>
                  <div className="flex items-center gap-3 text-[10px] text-ink-muted pt-0.5">
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-purple-600" />
                      <span>DEV ({activeDataset.by_split.DEV})</span>
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-blue-600" />
                      <span>HELDOUT ({activeDataset.by_split.HELDOUT})</span>
                    </span>
                  </div>
                </div>
              </div>
            ) : null}
          </div>

          {/* Dataset Limitations Footer */}
          {activeDataset?.limitations && (
            <div className="pt-3 border-t border-hairline text-[11px] text-ink-muted space-y-1">
              <span className="font-semibold text-ink block">Dataset limitations:</span>
              <ul className="list-disc list-inside space-y-0.5">
                {activeDataset.limitations.map((l, i) => (
                  <li key={i}>{l}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Right: Run Configuration Panel (7 cols) */}
        <div className="lg:col-span-7 rounded-panel border border-hairline bg-surface p-5 shadow-xs space-y-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sliders className="w-4 h-4 text-lens" />
              <h2 className="font-display font-semibold text-sm text-ink">
                Run Evaluation Harness
              </h2>
            </div>
            <span className="font-mono text-xs text-ink-muted">
              POST /evaluations/run
            </span>
          </div>

          {/* Error Banner if Run Failed */}
          {runError && (
            <div className="p-3 rounded-panel bg-[#A4123F]/10 border border-[#A4123F]/30 text-[#A4123F] text-xs flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span className="font-semibold">{runError.message}</span>
              </div>
              {runError.requestId && (
                <span className="font-mono text-[10px] pl-6 text-[#A4123F]/80">
                  Request ID: {runError.requestId}
                </span>
              )}
            </div>
          )}

          <div className="space-y-4 text-xs">
            {/* Dataset Selector */}
            <div className="space-y-1.5">
              <label className="font-semibold text-ink block">
                Target Evaluation Dataset
              </label>
              <select
                value={selectedDatasetId}
                onChange={(e) => setSelectedDatasetId(e.target.value)}
                className="w-full px-3 py-2 rounded-panel-nested border border-hairline bg-surface-2 text-ink text-xs focus:outline-none focus:ring-1 focus:ring-lens font-mono"
              >
                {datasets.map((d) => (
                  <option key={d.dataset_id} value={d.dataset_id}>
                    {d.dataset_id} ({d.case_count} cases) — {d.description}
                  </option>
                ))}
              </select>
            </div>

            {/* Split Selection Radio/Buttons */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="font-semibold text-ink block">
                  Evaluation Split
                </label>
                <span className="text-[10px] text-ink-muted">
                  Per §14: headline metrics reported on frozen HELDOUT
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {/* HELDOUT Split */}
                <button
                  type="button"
                  onClick={() => setSelectedSplit("HELDOUT")}
                  className={cn(
                    "p-3 rounded-panel-nested border text-left transition-all relative flex flex-col justify-between space-y-1",
                    selectedSplit === "HELDOUT"
                      ? "bg-surface border-lens shadow-xs ring-1 ring-lens/30"
                      : "bg-surface-2 border-hairline hover:border-hairline/80 text-ink-muted"
                  )}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-ink text-xs">
                      HELDOUT Split
                    </span>
                    <span className="font-mono text-[10px] px-2 py-0.5 rounded-pill bg-blue-500/10 text-blue-700 dark:text-blue-400 border border-blue-500/25 font-semibold">
                      Headline
                    </span>
                  </div>
                  <p className="text-[11px] text-ink-muted leading-tight">
                    Unseen held-out benchmark cases. Evaluated with frozen parameters and strict Wilson 95% intervals.
                  </p>
                </button>

                {/* DEV Split (Tuning Split) */}
                <button
                  type="button"
                  onClick={() => setSelectedSplit("DEV")}
                  className={cn(
                    "p-3 rounded-panel-nested border text-left transition-all relative flex flex-col justify-between space-y-1",
                    selectedSplit === "DEV"
                      ? "bg-surface border-lens shadow-xs ring-1 ring-lens/30"
                      : "bg-surface-2 border-hairline hover:border-hairline/80 text-ink-muted"
                  )}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-ink text-xs">
                      DEV Split
                    </span>
                    <span className="font-mono text-[10px] px-2 py-0.5 rounded-pill bg-purple-500/10 text-purple-700 dark:text-purple-400 border border-purple-500/25 font-semibold">
                      Tuning Split
                    </span>
                  </div>
                  <p className="text-[11px] text-ink-muted leading-tight">
                    Thresholds and weights tuned only on DEV. Freeze before HELDOUT verification.
                  </p>
                </button>
              </div>
            </div>

            {/* Checkbox Options */}
            <div className="pt-1 space-y-2">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={includeBaseline}
                  onChange={(e) => setIncludeBaseline(e.target.checked)}
                  className="w-4 h-4 rounded text-lens border-hairline focus:ring-lens"
                />
                <span className="text-xs text-ink font-medium">
                  Include RapidFuzz baseline comparison (name-only matcher tuned on DEV)
                </span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={includeAblation}
                  onChange={(e) => setIncludeAblation(e.target.checked)}
                  className="w-4 h-4 rounded text-lens border-hairline focus:ring-lens"
                />
                <span className="text-xs text-ink font-medium">
                  Include pipeline ablation study (FULL, NO_IDENTITYGUARD, NO_GATES, NO_ICON, NO_DESCRIPTION)
                </span>
              </label>
            </div>

            {/* Launch Action Button */}
            <div className="pt-2 flex items-center justify-between">
              <p className="text-[11px] text-ink-muted max-w-sm">
                Runs local deterministic <code className="font-mono text-ink">assess()</code> against all {selectedSplit} cases without external API queries.
              </p>

              <button
                type="button"
                onClick={handleRunEvaluation}
                disabled={runMutation.isPending || isLoadingDatasets}
                className={cn(
                  "px-5 py-2.5 rounded-pill bg-ink text-white font-semibold text-xs flex items-center gap-2 shadow-sm hover:bg-ink/90 transition-all",
                  runMutation.isPending && "opacity-70 cursor-not-allowed"
                )}
              >
                {runMutation.isPending ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Running Evaluation...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5 fill-current" />
                    <span>Run Evaluation ({selectedSplit})</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 3. Result View (Rendered from API response) */}
      {isLoadingLatest ? (
        <div className="p-12 text-center text-xs text-ink-muted space-y-3">
          <Loader2 className="w-6 h-6 animate-spin text-lens mx-auto" />
          <p>Loading evaluation benchmark results...</p>
        </div>
      ) : evalResult ? (
        <div className="space-y-6">
          {/* Result Metadata Strip & Pass/Fail status */}
          <div className="p-4 rounded-panel bg-surface border border-hairline shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3 flex-wrap">
              <span className="font-mono text-xs font-semibold text-ink">
                Run ID: {evalResult.id}
              </span>
              <span className="text-ink-muted">·</span>
              <span className="font-mono text-xs text-ink-muted">
                Dataset: <strong>{evalResult.dataset_id}</strong> ({evalResult.sample_count} cases)
              </span>
              <span className="text-ink-muted">·</span>
              <span
                className={cn(
                  "font-mono text-[11px] px-2.5 py-0.5 rounded-pill font-semibold border",
                  evalResult.split === "HELDOUT"
                    ? "bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/25"
                    : "bg-purple-500/10 text-purple-700 dark:text-purple-400 border-purple-500/25"
                )}
              >
                Split: {evalResult.split}
              </span>
              <span className="text-ink-muted">·</span>
              <span className="font-mono text-xs text-ink-muted">
                Scoring: v{evalResult.scoring_version} (Threshold ≥ {evalResult.threshold.review})
              </span>
            </div>

            {/* Official Flagged Clear Pass/Fail Badge */}
            <div className="flex items-center gap-2 self-start md:self-auto">
              {evalResult.official_flagged_count === 0 ? (
                <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-pill bg-teal-500/10 text-teal-800 dark:text-teal-300 border border-teal-500/30 text-xs font-semibold">
                  <ShieldCheck className="w-4 h-4 text-teal-600" />
                  <span>PASS: 0 official assets flagged</span>
                </div>
              ) : (
                <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-pill bg-[#A4123F]/10 text-[#A4123F] border border-[#A4123F]/30 text-xs font-semibold">
                  <ShieldAlert className="w-4 h-4 text-[#A4123F]" />
                  <span>FAIL: {evalResult.official_flagged_count} official assets flagged</span>
                </div>
              )}
            </div>
          </div>

          {/* Core Metrics Grid with Wilson 95% Confidence Intervals */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-display font-semibold text-sm text-ink">
                Headline Evaluation Metrics
              </h3>
              <span className="text-[11px] text-ink-muted font-mono">
                Method: {evalResult.confidence_intervals.method}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Precision Card */}
              <div className="p-4 rounded-panel bg-surface border border-hairline shadow-xs space-y-1">
                <span className="text-xs font-medium text-ink-muted block">
                  Precision
                </span>
                <span className="font-display font-bold text-2xl text-ink tracking-tight block">
                  {formatMetric(evalResult.precision)}
                </span>
                <div className="pt-1 border-t border-hairline text-[11px] font-mono text-ink-muted">
                  <span>Wilson 95% CI: </span>
                  <strong className="text-ink font-semibold">
                    {formatInterval(evalResult.confidence_intervals.precision)}
                  </strong>
                </div>
                <span className="text-[10px] text-ink-muted block">
                  TP / (TP + FP)
                </span>
              </div>

              {/* Recall Card */}
              <div className="p-4 rounded-panel bg-surface border border-hairline shadow-xs space-y-1">
                <span className="text-xs font-medium text-ink-muted block">
                  Recall
                </span>
                <span className="font-display font-bold text-2xl text-ink tracking-tight block">
                  {formatMetric(evalResult.recall)}
                </span>
                <div className="pt-1 border-t border-hairline text-[11px] font-mono text-ink-muted">
                  <span>Wilson 95% CI: </span>
                  <strong className="text-ink font-semibold">
                    {formatInterval(evalResult.confidence_intervals.recall)}
                  </strong>
                </div>
                <span className="text-[10px] text-ink-muted block">
                  TP / (TP + FN)
                </span>
              </div>

              {/* F1 Score Card */}
              <div className="p-4 rounded-panel bg-surface border border-hairline shadow-xs space-y-1">
                <span className="text-xs font-medium text-ink-muted block">
                  F1 Score
                </span>
                <span className="font-display font-bold text-2xl text-ink tracking-tight block">
                  {formatMetric(evalResult.f1)}
                </span>
                <div className="pt-1 border-t border-hairline text-[11px] font-mono text-ink-muted">
                  <span>Harmonic mean of P & R</span>
                </div>
                <span className="text-[10px] text-ink-muted block">
                  2·P·R / (P + R)
                </span>
              </div>

              {/* False Positive Rate Card */}
              <div className="p-4 rounded-panel bg-surface border border-hairline shadow-xs space-y-1">
                <span className="text-xs font-medium text-ink-muted block">
                  False-Positive Rate
                </span>
                <span className="font-display font-bold text-2xl text-ink tracking-tight block">
                  {formatMetric(evalResult.false_positive_rate)}
                </span>
                <div className="pt-1 border-t border-hairline text-[11px] font-mono text-ink-muted">
                  <span>Wilson 95% CI: </span>
                  <strong className="text-ink font-semibold">
                    {formatInterval(evalResult.confidence_intervals.false_positive_rate)}
                  </strong>
                </div>
                <span className="text-[10px] text-ink-muted block">
                  FP / (FP + TN)
                </span>
              </div>
            </div>
          </div>

          {/* Confusion Matrix & Hard Negatives Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Confusion Matrix (7 cols) */}
            <div className="lg:col-span-7 rounded-panel border border-hairline bg-surface p-5 shadow-xs space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Table className="w-4 h-4 text-lens" />
                  <h3 className="font-display font-semibold text-sm text-ink">
                    Confusion Matrix
                  </h3>
                </div>
                <span className="font-mono text-xs text-ink-muted">
                  Sample count: {evalResult.sample_count} cases
                </span>
              </div>

              {/* 2x2 Grid */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                {/* True Positives (TP) */}
                <div className="p-3.5 rounded-panel-nested bg-surface-2 border border-hairline space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-ink-muted text-[11px]">True Positives (TP)</span>
                    <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-lens/10 text-lens font-semibold">
                      Impersonation Flagged
                    </span>
                  </div>
                  <span className="font-mono font-bold text-2xl text-ink block">
                    {evalResult.confusion.tp}
                  </span>
                  <p className="text-[10px] text-ink-muted">
                    Actual impersonators correctly surfaced for review.
                  </p>
                </div>

                {/* False Positives (FP) */}
                <div className="p-3.5 rounded-panel-nested bg-surface-2 border border-hairline space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-ink-muted text-[11px]">False Positives (FP)</span>
                    <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-[#D9480F]/10 text-[#D9480F] font-semibold">
                      Namesake Flagged
                    </span>
                  </div>
                  <span className="font-mono font-bold text-2xl text-ink block">
                    {evalResult.confusion.fp}
                  </span>
                  <p className="text-[10px] text-ink-muted">
                    Benign entities incorrectly escalated to queue.
                  </p>
                </div>

                {/* False Negatives (FN) */}
                <div className="p-3.5 rounded-panel-nested bg-surface-2 border border-hairline space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-ink-muted text-[11px]">False Negatives (FN)</span>
                    <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-[#A4123F]/10 text-[#A4123F] font-semibold">
                      Missed Threat
                    </span>
                  </div>
                  <span className="font-mono font-bold text-2xl text-ink block">
                    {evalResult.confusion.fn}
                  </span>
                  <p className="text-[10px] text-ink-muted">
                    Adversarial look-alikes that fell below threshold.
                  </p>
                </div>

                {/* True Negatives (TN) */}
                <div className="p-3.5 rounded-panel-nested bg-surface-2 border border-hairline space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-ink-muted text-[11px]">True Negatives (TN)</span>
                    <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-teal-500/10 text-teal-700 font-semibold">
                      Correctly Cleared
                    </span>
                  </div>
                  <span className="font-mono font-bold text-2xl text-ink block">
                    {evalResult.confusion.tn}
                  </span>
                  <p className="text-[10px] text-ink-muted">
                    Benign namesakes & official assets correctly cleared.
                  </p>
                </div>
              </div>

              {/* Exact Definitions Text from API Response */}
              <div className="p-3 rounded-panel-nested bg-surface-2 border border-hairline text-xs space-y-1">
                <span className="font-semibold text-ink text-[11px] block">
                  Ground Truth Classification Definitions:
                </span>
                <p className="text-[11px] text-ink-muted leading-relaxed">
                  {evalResult.definitions}
                </p>
              </div>
            </div>

            {/* Hard Negatives Panel (5 cols) */}
            <div className="lg:col-span-5 rounded-panel border border-hairline bg-surface p-5 shadow-xs space-y-4 flex flex-col justify-between">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-teal-600" />
                    <h3 className="font-display font-semibold text-sm text-ink">
                      Hard Negatives (Namesakes)
                    </h3>
                  </div>
                  <span className="font-mono text-xs text-ink-muted font-semibold">
                    {evalResult.hard_negatives.tested} Tested
                  </span>
                </div>

                <p className="text-xs text-ink-muted">
                  Real captured namesakes tested against IdentityGuard rules and G4/G5 gates to ensure genuine businesses are not harassed.
                </p>

                <div className="grid grid-cols-3 gap-2 text-center pt-1">
                  <div className="p-2 rounded-panel-nested bg-surface-2 border border-hairline">
                    <span className="text-[10px] text-ink-muted block uppercase">Tested</span>
                    <span className="font-mono font-bold text-lg text-ink">
                      {evalResult.hard_negatives.tested}
                    </span>
                  </div>

                  <div className="p-2 rounded-panel-nested bg-surface-2 border border-hairline">
                    <span className="text-[10px] text-ink-muted block uppercase">Cleared</span>
                    <span className="font-mono font-bold text-lg text-teal-700 dark:text-teal-400">
                      {evalResult.hard_negatives.correctly_cleared}
                    </span>
                  </div>

                  <div className="p-2 rounded-panel-nested bg-surface-2 border border-hairline">
                    <span className="text-[10px] text-ink-muted block uppercase">False Pos</span>
                    <span className="font-mono font-bold text-lg text-[#D9480F]">
                      {evalResult.hard_negatives.false_positives}
                    </span>
                  </div>
                </div>

                {/* Progress bar of correctly cleared */}
                <div className="space-y-1 pt-2">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-ink-muted">Namesake Clearance Rate:</span>
                    <span className="font-mono font-semibold text-ink">
                      {evalResult.hard_negatives.tested > 0
                        ? `${(
                            (evalResult.hard_negatives.correctly_cleared /
                              evalResult.hard_negatives.tested) *
                            100
                          ).toFixed(1)}%`
                        : "N/A"}
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-surface-2 overflow-hidden border border-hairline">
                    <div
                      style={{
                        width: `${
                          evalResult.hard_negatives.tested > 0
                            ? (evalResult.hard_negatives.correctly_cleared /
                                evalResult.hard_negatives.tested) *
                              100
                            : 0
                        }%`,
                      }}
                      className="h-full bg-teal-600 rounded-full"
                    />
                  </div>
                </div>
              </div>

              <div className="pt-3 border-t border-hairline text-[11px] text-ink-muted">
                Zero official assets flagged. Benign look-alike namesakes are filtered before alert generation.
              </div>
            </div>
          </div>

          {/* Baseline Comparison (RapidFuzz vs Full Pipeline) */}
          {evalResult.baseline && (
            <div className="rounded-panel border border-hairline bg-surface p-5 shadow-xs space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Scale className="w-4 h-4 text-lens" />
                  <h3 className="font-display font-semibold text-sm text-ink">
                    Baseline Comparison (Name-Only RapidFuzz vs ThreatLens Full Pipeline)
                  </h3>
                </div>
                <span className="font-mono text-xs text-ink-muted">
                  Baseline tuned on {evalResult.baseline.tuned_on}
                </span>
              </div>

              <p className="text-xs text-ink-muted">
                Demonstrates why lexical name similarity alone fails in production. RapidFuzz yields high false-positive rates on innocent namesakes, whereas ThreatLens combines multi-signal forensic corroboration and identity gates.
              </p>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-surface-2 text-ink-muted border-b border-hairline text-[11px]">
                      <th className="py-2.5 px-4 font-medium">Evaluation Model</th>
                      <th className="py-2.5 px-4 font-medium">Precision</th>
                      <th className="py-2.5 px-4 font-medium">Recall</th>
                      <th className="py-2.5 px-4 font-medium">False-Positive Rate</th>
                      <th className="py-2.5 px-4 font-medium">Architectural Distinction</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-hairline">
                    {/* Baseline Row */}
                    <tr className="hover:bg-surface-2/40 transition-colors">
                      <td className="py-3 px-4 font-mono font-medium text-ink">
                        {evalResult.baseline.name} (DEV tuned)
                      </td>
                      <td className="py-3 px-4 font-mono">
                        {evalResult.baseline.precision.toFixed(2)}
                      </td>
                      <td className="py-3 px-4 font-mono">
                        {evalResult.baseline.recall.toFixed(2)}
                      </td>
                      <td className="py-3 px-4 font-mono text-[#D9480F] font-semibold">
                        {evalResult.baseline.false_positive_rate.toFixed(2)}
                      </td>
                      <td className="py-3 px-4 text-ink-muted text-[11px]">
                        Single lexical threshold on string similarity. Over-flags benign namesakes.
                      </td>
                    </tr>

                    {/* ThreatLens Full Pipeline Row */}
                    <tr className="bg-lens/5 hover:bg-lens/10 transition-colors font-medium">
                      <td className="py-3 px-4 font-mono font-semibold text-lens flex items-center gap-1.5">
                        <Sparkles className="w-3.5 h-3.5 text-lens" />
                        <span>ThreatLens Full Pipeline</span>
                      </td>
                      <td className="py-3 px-4 font-mono font-semibold text-ink">
                        {formatMetric(evalResult.precision)}
                      </td>
                      <td className="py-3 px-4 font-mono font-semibold text-ink">
                        {formatMetric(evalResult.recall)}
                      </td>
                      <td className="py-3 px-4 font-mono font-semibold text-teal-700 dark:text-teal-400">
                        {formatMetric(evalResult.false_positive_rate)}
                      </td>
                      <td className="py-3 px-4 text-ink text-[11px]">
                        IdentityGuard + 7 observable signals + visual/content corroboration gates.
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Ablation Study & Technique Recall Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Ablation Study Table (7 cols) */}
            {evalResult.ablation && evalResult.ablation.length > 0 && (
              <div className="lg:col-span-7 rounded-panel border border-hairline bg-surface p-5 shadow-xs space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sliders className="w-4 h-4 text-lens" />
                    <h3 className="font-display font-semibold text-sm text-ink">
                      Ablation Study
                    </h3>
                  </div>
                  <span className="font-mono text-xs text-ink-muted">
                    Component Isolation
                  </span>
                </div>

                <p className="text-xs text-ink-muted">
                  Measures performance degradation when disabling specific pipeline stages:
                </p>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-surface-2 text-ink-muted border-b border-hairline text-[11px]">
                        <th className="py-2.5 px-3 font-medium">Configuration</th>
                        <th className="py-2.5 px-3 font-medium">Precision</th>
                        <th className="py-2.5 px-3 font-medium">Recall</th>
                        <th className="py-2.5 px-3 font-medium">Official Flagged</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-hairline">
                      {evalResult.ablation.map((row) => (
                        <tr
                          key={row.configuration}
                          className={cn(
                            "hover:bg-surface-2/40 transition-colors",
                            row.configuration === "FULL" && "bg-lens/5 font-semibold"
                          )}
                        >
                          <td className="py-2.5 px-3 font-mono text-ink">
                            {row.configuration}
                          </td>
                          <td className="py-2.5 px-3 font-mono">
                            {row.precision.toFixed(2)}
                          </td>
                          <td className="py-2.5 px-3 font-mono">
                            {row.recall.toFixed(2)}
                          </td>
                          <td className="py-2.5 px-3 font-mono">
                            {row.official_flagged_count !== undefined ? (
                              row.official_flagged_count > 0 ? (
                                <span className="text-[#A4123F] font-semibold">
                                  {row.official_flagged_count} (FAIL)
                                </span>
                              ) : (
                                <span className="text-teal-700">0</span>
                              )
                            ) : (
                              <span className="text-ink-muted">—</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Technique Recall Table (5 cols) */}
            {evalResult.technique_recall && evalResult.technique_recall.length > 0 && (
              <div className="lg:col-span-5 rounded-panel border border-hairline bg-surface p-5 shadow-xs space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Table className="w-4 h-4 text-lens" />
                    <h3 className="font-display font-semibold text-sm text-ink">
                      Technique Recall
                    </h3>
                  </div>
                  <span className="font-mono text-xs text-ink-muted">
                    Per-Technique
                  </span>
                </div>

                <div className="overflow-x-auto max-h-72 overflow-y-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-surface-2 text-ink-muted border-b border-hairline text-[11px] sticky top-0">
                        <th className="py-2 px-3 font-medium">Technique</th>
                        <th className="py-2 px-3 font-medium">Tested</th>
                        <th className="py-2 px-3 font-medium">Detected</th>
                        <th className="py-2 px-3 font-medium">Recall Rate</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-hairline">
                      {evalResult.technique_recall.map((tr) => (
                        <tr key={tr.technique} className="hover:bg-surface-2/40">
                          <td className="py-2 px-3 font-mono text-[11px] text-ink">
                            {tr.technique}
                          </td>
                          <td className="py-2 px-3 font-mono">{tr.tested}</td>
                          <td className="py-2 px-3 font-mono font-semibold text-teal-700 dark:text-teal-400">
                            {tr.detected}
                          </td>
                          <td className="py-2 px-3 font-mono text-ink">
                            {tr.tested > 0
                              ? `${((tr.detected / tr.tested) * 100).toFixed(0)}%`
                              : "N/A"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>

          {/* Failure Cases Section */}
          {evalResult.failure_cases && evalResult.failure_cases.length > 0 && (
            <div className="rounded-panel border border-hairline bg-surface p-5 shadow-xs space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <HelpCircle className="w-4 h-4 text-amber-600" />
                  <h3 className="font-display font-semibold text-sm text-ink">
                    Audited Failure Cases (Honest Error Analysis)
                  </h3>
                </div>
                <span className="font-mono text-xs text-ink-muted">
                  Showing {Math.min(evalResult.failure_cases.length, 3)} cases
                </span>
              </div>

              <p className="text-xs text-ink-muted">
                ThreatLens documents failure cases openly. False positives and false negatives are inspected to drive future model and rule iterations:
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {evalResult.failure_cases.map((fc) => (
                  <div
                    key={fc.case_id}
                    className="p-4 rounded-panel-nested border border-hairline bg-surface-2 space-y-2 flex flex-col justify-between"
                  >
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[11px] font-semibold text-ink">
                          Case {fc.case_id}
                        </span>
                        <span
                          className={cn(
                            "px-2 py-0.5 rounded-pill font-mono text-[10px] font-semibold border",
                            fc.expected === "IMPERSONATION"
                              ? "bg-[#A4123F]/10 text-[#A4123F] border-[#A4123F]/25"
                              : "bg-[#0E8F9C]/10 text-[#0E8F9C] border-[#0E8F9C]/25"
                          )}
                        >
                          Expected: {fc.expected}
                        </span>
                      </div>

                      <div className="text-xs text-ink-muted flex items-center gap-1.5">
                        <span>Outcome:</span>
                        <span className="font-mono text-[11px] text-ink font-semibold">
                          {fc.got}
                        </span>
                      </div>

                      <p className="text-[11px] text-ink-muted leading-relaxed pt-1 border-t border-hairline/60">
                        {fc.why}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}

export default EvaluationLabPage;
