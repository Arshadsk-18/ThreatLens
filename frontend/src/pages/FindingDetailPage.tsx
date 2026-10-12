import React, { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import { ApiError } from "@/api/errors";
import { MOCK_FINDINGS } from "@/api/mock-data/fixtures";
import { SeverityPill } from "@/components/cx/SeverityPill";
import { SourceBadge } from "@/components/cx/SourceBadge";
import { StatusPill } from "@/components/cx/StatusPill";
import { ScoreBar } from "@/components/cx/ScoreBar";
import { CoverageMeter } from "@/components/cx/CoverageMeter";
import { AssetIcon } from "@/components/cx/AssetIcon";
import { NameDiff } from "@/components/cx/NameDiff";
import { DecisionDialog } from "./findings/DecisionDialog";
import {
  ArrowLeft,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Info,
  ExternalLink,
  FileText,
  History,
  Scale,
  Layers,
} from "lucide-react";
import { cn } from "@/lib/utils";

export function FindingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const findingId = id || MOCK_FINDINGS[0].id;

  const [activeTab, setActiveTab] = useState<"compare" | "evidence" | "history">("compare");
  const [decisionOpen, setDecisionOpen] = useState(false);

  const {
    data: finding,
    isLoading: isLoadingFinding,
    error: findingError,
  } = useQuery({
    queryKey: ["finding", findingId],
    queryFn: () => apiClient.getFinding(findingId),
  });

  const {
    data: comparison,
    isLoading: isLoadingComp,
  } = useQuery({
    queryKey: ["finding-comparison", findingId],
    queryFn: () => apiClient.getFindingComparison(findingId),
    enabled: !!finding,
  });

  if (isLoadingFinding) {
    return (
      <div className="space-y-6 animate-pulse" aria-busy="true">
        <div className="h-6 w-32 bg-surface-2 rounded-pill" />
        <div className="h-28 bg-surface rounded-panel border border-hairline" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 h-96 bg-surface rounded-panel border border-hairline" />
          <div className="h-96 bg-surface rounded-panel border border-hairline" />
        </div>
      </div>
    );
  }

  if (findingError || !finding) {
    return (
      <div className="p-8 rounded-panel bg-surface border border-hairline text-center space-y-4 max-w-lg mx-auto mt-12">
        <div className="w-12 h-12 rounded-full bg-risk-critical/10 text-risk-critical flex items-center justify-center mx-auto">
          <AlertTriangle className="w-6 h-6" />
        </div>
        <h2 className="font-display font-semibold text-lg text-ink">Finding Not Found</h2>
        <p className="text-xs text-ink-muted">
          {findingError instanceof ApiError ? findingError.message : `Could not locate finding record ${findingId}.`}
        </p>
        {findingError instanceof ApiError && findingError.requestId && (
          <span className="font-mono text-[10px] text-ink-muted block">
            Request ID: {findingError.requestId}
          </span>
        )}
        <Link
          to="/findings"
          className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-pill bg-ink text-white hover:bg-ink/90 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Return to Review Queue</span>
        </Link>
      </div>
    );
  }

  // Gates logic
  const gates = finding.gates_applied || [];
  const hasG2orG3 = gates.includes("G2") || gates.includes("G3");
  const isCoverageBelowHalf = finding.evidence_coverage < 0.5;

  // Corroborating groups plain language line
  const corroboratingGroupsFormatted =
    finding.corroborating_groups && finding.corroborating_groups.length > 0
      ? finding.corroborating_groups
          .map((g) => g.charAt(0) + g.slice(1).toLowerCase())
          .join(", ")
      : "None";

  // Comparison details extraction
  const displayNameComp = comparison?.comparisons.find((c) => c.field === "display_name");
  const iconComp = comparison?.comparisons.find((c) => c.field === "icon");
  const descComp = comparison?.comparisons.find((c) => c.field === "description");

  const nonAsciiChars = displayNameComp?.non_ascii_chars || [];
  const nameDiffSegments = displayNameComp?.name_diff || [];

  return (
    <div className="space-y-6">
      {/* Back navigation and Breadcrumb */}
      <div className="flex items-center justify-between">
        <Link
          to="/findings"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-ink-muted hover:text-ink transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Findings Queue</span>
        </Link>
        <span className="font-mono text-[11px] text-ink-muted">
          ID: {finding.id}
        </span>
      </div>

      {/* Detail Header Strip */}
      <header className="p-5 rounded-panel bg-surface border border-hairline shadow-xs space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="font-display font-bold text-xl sm:text-2xl text-ink">
                {finding.candidate.display_name}
              </h1>
              <SourceBadge mode={finding.source_mode} />
              <SeverityPill severity={finding.severity} />
              <StatusPill status={finding.status} />
            </div>
            <div className="flex flex-wrap items-center gap-2.5 text-xs text-ink-muted">
              <span className="capitalize font-medium text-ink">
                Platform: {finding.candidate.platform.replace(/_/g, " ")}
              </span>
              <span>·</span>
              <span className="font-mono font-medium px-2 py-0.5 rounded-pill bg-surface-2 border border-hairline text-ink">
                Technique: {finding.technique}
              </span>
              <span>·</span>
              <span>Observed: {new Date(finding.observed_at).toLocaleString()}</span>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2.5 shrink-0">
            {/* P1 Reserved Report Button */}
            <button
              disabled
              aria-disabled="true"
              title="Evidence report export is reserved for P1"
              className="opacity-50 cursor-not-allowed px-3.5 py-2 text-xs font-semibold rounded-pill border border-hairline bg-surface-2 text-ink-muted flex items-center gap-1.5"
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Evidence report</span>
            </button>

            {/* Decision Dialog Control */}
            <button
              onClick={() => setDecisionOpen(true)}
              className="px-4 py-2 text-xs font-semibold text-white bg-ink rounded-pill hover:bg-ink/90 transition-all shadow-sm flex items-center gap-1.5"
            >
              <Scale className="w-3.5 h-3.5" />
              <span>Record Decision</span>
            </button>
          </div>
        </div>

        {/* Risk Score Banner with explicit non-probability phrasing */}
        <div className="p-3.5 rounded-panel-nested bg-surface-2 border border-hairline flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="px-3 py-1.5 rounded-nested bg-surface border border-hairline font-display font-bold text-lg text-ink">
              {finding.risk_score} <span className="text-xs font-normal text-ink-muted">/ 100</span>
            </div>
            <div>
              <span className="text-xs font-semibold text-ink block">
                Risk score {finding.risk_score} / 100 (not a probability)
              </span>
              <span className="text-[11px] text-ink-muted">
                Composite forensic risk index based on observed observable signals.
              </span>
            </div>
          </div>

          <div className="w-full sm:w-48">
            <ScoreBar value={finding.risk_score} max={100} />
          </div>
        </div>
      </header>

      {/* Main 2-Column Register Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Left Column (2 spans): "How this score was built" */}
        <div className="lg:col-span-2 space-y-6">
          <section className="p-5 rounded-panel bg-surface border border-hairline shadow-xs space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-hairline">
              <div>
                <h2 className="font-display font-semibold text-base text-ink">
                  How this score was built
                </h2>
                <p className="text-xs text-ink-muted">
                  Horizontal points breakdown across evidence signals
                </p>
              </div>
              <span className="font-mono text-xs font-semibold px-2.5 py-1 rounded-pill bg-surface-2 border border-hairline text-ink">
                Total: {finding.risk_score} pts
              </span>
            </div>

            {/* Signals list */}
            <div className="space-y-3">
              {finding.score_breakdown && finding.score_breakdown.length > 0 ? (
                finding.score_breakdown.map((sb, idx) => {
                  const isUnavailable = sb.status === "UNAVAILABLE";
                  return (
                    <div
                      key={sb.signal || idx}
                      className={cn(
                        "p-3.5 rounded-panel-nested border transition-all space-y-2",
                        isUnavailable
                          ? "border-dashed border-hairline bg-[repeating-linear-gradient(45deg,transparent,transparent_6px,rgba(0,0,0,0.03)_6px,rgba(0,0,0,0.03)_12px)] opacity-85"
                          : "bg-surface-2 border-hairline"
                      )}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-semibold text-ink">
                            {sb.signal.replace(/_/g, " ")}
                          </span>
                          {/* Group badge */}
                          <span className="px-2 py-0.5 rounded-pill bg-surface border border-hairline text-[10px] font-semibold text-ink-muted uppercase">
                            {sb.group}
                          </span>
                          {/* Status badge */}
                          <span
                            className={cn(
                              "px-2 py-0.5 rounded-pill text-[10px] font-semibold border",
                              sb.status === "OBSERVED" && "bg-teal-500/10 text-teal-700 dark:text-teal-400 border-teal-500/30",
                              sb.status === "INFERRED" && "bg-lens/10 text-lens border-lens/30",
                              sb.status === "UNAVAILABLE" && "bg-hairline text-ink-muted border-hairline",
                              sb.status === "SIMULATED" && "bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/30"
                            )}
                          >
                            {sb.status}
                          </span>
                        </div>
                        <span className="font-mono font-semibold text-ink">
                          {sb.points} / {sb.max_points} pts
                        </span>
                      </div>

                      {/* Score bar */}
                      <ScoreBar value={sb.points} max={sb.max_points} />

                      {/* Signal reason */}
                      {isUnavailable ? (
                        <p className="text-[11px] text-ink-muted font-medium italic">
                          Not observed. Counts as zero and lowers evidence coverage. This is not a sign of safety.
                        </p>
                      ) : (
                        <p className="text-[11px] text-ink-muted">{sb.reason}</p>
                      )}
                    </div>
                  );
                })
              ) : (
                <div className="p-4 rounded-panel-nested bg-surface-2 border border-hairline text-xs text-ink-muted">
                  No detailed score breakdown recorded for this finding.
                </div>
              )}
            </div>

            {/* Plain-language line for corroborating groups */}
            <div className="p-3.5 rounded-panel-nested bg-surface-2 border border-hairline text-xs text-ink space-y-1">
              <span className="font-semibold block">
                Corroborating groups: {corroboratingGroupsFormatted}. The name group never counts as corroboration.
              </span>
              <p className="text-[11px] text-ink-muted">
                Section 11.5 safeguard: Identity confirmation requires independent verification beyond lexical string matching.
              </p>
            </div>
          </section>
        </div>

        {/* Right Column (1 span): Stacked Rail Cards */}
        <div className="space-y-4">
          {/* Card 1: IdentityGuard result */}
          <div className="p-4 rounded-panel bg-surface border border-hairline shadow-xs space-y-2.5">
            <div className="flex items-center gap-2 text-xs font-semibold text-ink">
              <ShieldCheck className="w-4 h-4 text-lens" />
              <span>IdentityGuard Result</span>
            </div>
            <div className="p-2.5 rounded-panel-nested bg-surface-2 border border-hairline text-xs space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-ink-muted">Decision:</span>
                <span className="font-mono font-semibold text-ink">
                  {finding.identity_guard?.decision || "CANDIDATE_FOR_REVIEW"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-ink-muted">Rule:</span>
                <span className="font-mono text-[11px] text-ink">
                  {finding.identity_guard?.rule || "NO_EXACT_OR_PUBLISHER_MATCH"}
                </span>
              </div>
              <p className="text-[11px] text-ink-muted pt-1 border-t border-hairline">
                {finding.identity_guard?.explanation ||
                  "No registered identifier matches. Name similarity does not prove official status."}
              </p>
            </div>
          </div>

          {/* Card 2: Gates Applied */}
          <div className="p-4 rounded-panel bg-surface border border-hairline shadow-xs space-y-2.5">
            <div className="flex items-center gap-2 text-xs font-semibold text-ink">
              <Layers className="w-4 h-4 text-ink" />
              <span>Gates Applied</span>
            </div>
            <div className="p-2.5 rounded-panel-nested bg-surface-2 border border-hairline text-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-ink-muted">Applied Gates:</span>
                <span className="font-mono font-semibold text-ink">
                  {gates.length > 0 ? gates.join(", ") : "None"}
                </span>
              </div>

              {hasG2orG3 && (
                <div className="p-2 rounded bg-risk-medium/10 border border-risk-medium/30 text-risk-medium text-[11px] font-semibold space-y-1">
                  <span>Score capped at 49</span>
                  {isCoverageBelowHalf && (
                    <p className="font-normal text-ink">
                      Insufficient evidence: only the name could be observed.
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Card 3: Evidence Coverage */}
          <div className="p-4 rounded-panel bg-surface border border-hairline shadow-xs space-y-2.5">
            <CoverageMeter coverage={finding.evidence_coverage} />
          </div>

          {/* Card 4: Limitations (verbatim from API) */}
          <div className="p-4 rounded-panel bg-surface border border-hairline shadow-xs space-y-2.5">
            <div className="flex items-center gap-2 text-xs font-semibold text-ink">
              <Info className="w-4 h-4 text-ink-muted" />
              <span>Limitations</span>
            </div>
            {finding.limitations && finding.limitations.length > 0 ? (
              <ul className="text-xs text-ink-muted list-disc list-inside space-y-1">
                {finding.limitations.map((limit, idx) => (
                  <li key={idx} className="leading-snug">
                    {limit}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-ink-muted italic">No specific limitations reported by scoring engine.</p>
            )}
          </div>
        </div>
      </div>

      {/* Primary forensic tabs: Evidence Compare | Observed Evidence | Decision History */}
      <section className="p-5 rounded-panel bg-surface border border-hairline shadow-xs space-y-5">
        <div className="flex items-center gap-2 border-b border-hairline pb-3">
          {[
            { id: "compare" as const, label: "Evidence Compare", icon: Scale },
            { id: "evidence" as const, label: "Observed Evidence", icon: ShieldAlert },
            { id: "history" as const, label: "Decision History", icon: History },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  "px-4 py-2 text-xs font-semibold rounded-pill flex items-center gap-2 transition-all",
                  isActive
                    ? "bg-ink text-white shadow-xs"
                    : "bg-surface-2 text-ink-muted hover:text-ink hover:bg-surface border border-hairline"
                )}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* TAB 1: EVIDENCE COMPARE */}
        {activeTab === "compare" && (
          <div className="space-y-6">
            {isLoadingComp ? (
              <div className="p-8 text-center text-xs text-ink-muted animate-pulse">
                Loading side-by-side comparison...
              </div>
            ) : comparison ? (
              <div className="space-y-6">
                {/* Forensic Character Name Diff */}
                <div className="space-y-2">
                  <NameDiff
                    official={comparison.official_asset?.display_name || "Kaveri Bank"}
                    candidate={comparison.candidate_asset.display_name}
                    diffSegments={nameDiffSegments}
                    nonAsciiChars={nonAsciiChars}
                    technique={finding.technique}
                  />

                  {/* Plain sentence for non-ASCII homoglyph inspection */}
                  {nonAsciiChars.length > 0 && (
                    <div className="p-3 rounded-panel-nested bg-surface-2 border border-hairline text-xs text-ink font-medium">
                      Contains {nonAsciiChars.length} non-ASCII character:{" "}
                      {nonAsciiChars.map((c) => `${c.char} (${c.codepoint}) at position ${c.index}`).join(", ")}.
                    </div>
                  )}

                  {/* Plain similarity score representation */}
                  {displayNameComp?.similarity !== undefined && displayNameComp?.similarity !== null && (
                    <div className="flex items-center justify-between text-xs px-2 text-ink-muted">
                      <span>Name Lexical Similarity:</span>
                      <span className="font-mono font-semibold text-ink">
                        {displayNameComp.similarity.toFixed(2)} (similarity index, not a percentage claim)
                      </span>
                    </div>
                  )}
                </div>

                {/* Side-by-side Comparative Attributes Table */}
                <div className="border border-hairline rounded-nested overflow-hidden">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-surface-2 text-ink-muted border-b border-hairline uppercase text-[10px] tracking-wider">
                      <tr>
                        <th className="px-4 py-3 w-1/4">Forensic Dimension</th>
                        <th className="px-4 py-3 w-3/8 border-l border-hairline">
                          Registered Official Reference
                        </th>
                        <th className="px-4 py-3 w-3/8 border-l border-hairline">
                          Observed Candidate
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-hairline bg-surface text-ink">
                      {/* Icon Comparison */}
                      <tr>
                        <td className="px-4 py-3 font-semibold text-ink-muted">
                          Icon / Avatar
                        </td>
                        <td className="px-4 py-3 border-l border-hairline">
                          <div className="flex items-center gap-3">
                            <AssetIcon
                              iconUrl={comparison.official_asset?.icon_url || null}
                              name={comparison.official_asset?.display_name || "Official"}
                              className="w-12 h-12 rounded-nested shadow-xs"
                            />
                            <span className="text-[11px] text-ink-muted">Official Store Asset</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 border-l border-hairline">
                          <div className="flex items-center gap-3">
                            <AssetIcon
                              iconUrl={comparison.candidate_asset.icon_url || null}
                              name={comparison.candidate_asset.display_name}
                              className="w-12 h-12 rounded-nested shadow-xs"
                            />
                            <div className="space-y-0.5">
                              <span className="text-[11px] font-semibold block text-ink">
                                Candidate Icon
                              </span>
                              {iconComp && (
                                <p className="text-[11px] text-ink-muted">
                                  Icon perceptual hash is{" "}
                                  {Math.round((iconComp.similarity || 0.93) * 100)}% similar. Hash similarity is not proof of copying.
                                </p>
                              )}
                            </div>
                          </div>
                        </td>
                      </tr>

                      {/* Publisher comparison: Neutral styling per contract 8.2 */}
                      <tr>
                        <td className="px-4 py-3 font-semibold text-ink-muted">
                          Publisher Name
                        </td>
                        <td className="px-4 py-3 border-l border-hairline">
                          <span className="font-medium">
                            {comparison.official_asset?.publisher_name || "Registered Bank Entity"}
                          </span>
                        </td>
                        <td className="px-4 py-3 border-l border-hairline">
                          <div className="space-y-0.5">
                            <span className="font-medium text-ink">
                              {comparison.candidate_asset.publisher_name || "Unverified Publisher"}
                            </span>
                            <span className="text-[11px] text-ink-muted block">
                              Publisher difference recorded as observable fact.
                            </span>
                          </div>
                        </td>
                      </tr>

                      {/* Developer Identifier */}
                      <tr>
                        <td className="px-4 py-3 font-semibold text-ink-muted">
                          Developer / Account ID
                        </td>
                        <td className="px-4 py-3 border-l border-hairline">
                          <span className="font-mono text-[11px] text-ink">
                            {comparison.official_asset?.developer_id || "dev-official-900"}
                          </span>
                        </td>
                        <td className="px-4 py-3 border-l border-hairline">
                          <span className="font-mono text-[11px] text-ink">
                            {comparison.candidate_asset.developer_id || "Unregistered Identifier"}
                          </span>
                        </td>
                      </tr>

                      {/* Category */}
                      <tr>
                        <td className="px-4 py-3 font-semibold text-ink-muted">
                          Catalog Category
                        </td>
                        <td className="px-4 py-3 border-l border-hairline">
                          <span>{comparison.official_asset?.category || "Finance"}</span>
                        </td>
                        <td className="px-4 py-3 border-l border-hairline">
                          <span>{comparison.candidate_asset.category || "Unknown"}</span>
                        </td>
                      </tr>

                      {/* Canonical URLs */}
                      <tr>
                        <td className="px-4 py-3 font-semibold text-ink-muted">
                          Canonical Store / Web URL
                        </td>
                        <td className="px-4 py-3 border-l border-hairline">
                          {comparison.official_asset?.canonical_url ? (
                            <a
                              href={comparison.official_asset.canonical_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-lens hover:underline inline-flex items-center gap-1 font-mono text-[11px]"
                            >
                              <span>Official Link</span>
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          ) : (
                            <span className="text-ink-muted italic">None</span>
                          )}
                        </td>
                        <td className="px-4 py-3 border-l border-hairline">
                          {comparison.candidate_asset.canonical_url ? (
                            <a
                              href={comparison.candidate_asset.canonical_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-lens hover:underline inline-flex items-center gap-1 font-mono text-[11px]"
                            >
                              <span>Candidate Link</span>
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          ) : (
                            <span className="text-ink-muted italic">None</span>
                          )}
                        </td>
                      </tr>

                      {/* Description comparison */}
                      <tr>
                        <td className="px-4 py-3 font-semibold text-ink-muted">
                          Description
                        </td>
                        <td className="px-4 py-3 border-l border-hairline text-ink-muted text-[11px] leading-relaxed">
                          Official mobile banking application for Kaveri Bank customers.
                        </td>
                        <td className="px-4 py-3 border-l border-hairline text-ink text-[11px] leading-relaxed">
                          <div className="space-y-1">
                            <p>{finding.candidate.description || "No description provided."}</p>
                            {descComp && descComp.similarity !== null && (
                              <span className="text-[10px] text-ink-muted font-mono block">
                                Text similarity index: {descComp.similarity.toFixed(2)}
                              </span>
                            )}
                          </div>
                        </td>
                      </tr>

                      {/* Specific social account fields if SOCIAL_ACCOUNT */}
                      {finding.candidate.asset_type === "SOCIAL_ACCOUNT" && (
                        <>
                          <tr>
                            <td className="px-4 py-3 font-semibold text-ink-muted">
                              Handle
                            </td>
                            <td className="px-4 py-3 border-l border-hairline font-mono text-[11px]">
                              @kaveribank.example
                            </td>
                            <td className="px-4 py-3 border-l border-hairline font-mono text-[11px]">
                              @{finding.candidate.handle || "unregistered"}
                            </td>
                          </tr>
                          <tr>
                            <td className="px-4 py-3 font-semibold text-ink-muted">
                              Follower Count & Footprint
                            </td>
                            <td className="px-4 py-3 border-l border-hairline text-ink-muted">
                              Verified Official Presence
                            </td>
                            <td className="px-4 py-3 border-l border-hairline">
                              {finding.candidate.followers !== null && finding.candidate.followers !== undefined
                                ? `${finding.candidate.followers} followers`
                                : "Unreported"}
                            </td>
                          </tr>
                          <tr>
                            <td className="px-4 py-3 font-semibold text-ink-muted">
                              Account Creation Date
                            </td>
                            <td className="px-4 py-3 border-l border-hairline text-ink-muted">
                              Established 2024
                            </td>
                            <td className="px-4 py-3 border-l border-hairline">
                              {finding.candidate.created_at_source
                                ? new Date(finding.candidate.created_at_source).toLocaleDateString()
                                : "Unreported"}
                            </td>
                          </tr>
                        </>
                      )}
                    </tbody>
                  </table>
                </div>

                {/* Evidence Compare Footer */}
                <footer className="p-4 rounded-panel-nested bg-surface-2 border border-hairline text-xs space-y-2">
                  <p className="text-ink font-medium italic">
                    "{comparison.disclaimer}"
                  </p>
                  <div className="flex flex-wrap items-center justify-between text-[11px] text-ink-muted pt-2 border-t border-hairline">
                    <span>Source: {finding.source_mode}</span>
                    <span>Observed: {new Date(finding.observed_at).toLocaleString()}</span>
                    <span>Scoring Engine Version: {finding.scoring_version}</span>
                  </div>
                </footer>
              </div>
            ) : null}
          </div>
        )}

        {/* TAB 2: OBSERVED EVIDENCE TABLE */}
        {activeTab === "evidence" && (
          <div className="space-y-4">
            {/* Explanation text from API in a quote block, not rewritten */}
            <div className="space-y-1">
              <span className="text-xs font-semibold text-ink-muted uppercase tracking-wider">
                Scoring Engine Assessment
              </span>
              <blockquote className="p-4 rounded-panel-nested bg-surface-2 border-l-4 border-lens text-xs text-ink leading-relaxed">
                "{finding.explanation}"
              </blockquote>
            </div>

            <div className="border border-hairline rounded-nested overflow-hidden">
              <table className="w-full text-xs text-left">
                <thead className="bg-surface-2 text-ink-muted border-b border-hairline uppercase text-[10px] tracking-wider">
                  <tr>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3">Field</th>
                    <th className="px-4 py-3">Observed Value</th>
                    <th className="px-4 py-3">Source</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Observed At</th>
                    <th className="px-4 py-3">Source URL</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-hairline bg-surface text-ink">
                  {finding.evidence && finding.evidence.length > 0 ? (
                    finding.evidence.map((ev) => (
                      <tr key={ev.id}>
                        <td className="px-4 py-3 font-mono text-[11px] font-semibold text-ink">
                          {ev.evidence_type}
                        </td>
                        <td className="px-4 py-3 font-mono text-[11px] text-ink-muted">
                          {ev.field_name}
                        </td>
                        <td className="px-4 py-3 max-w-xs truncate" title={ev.observed_value}>
                          {ev.observed_value}
                        </td>
                        <td className="px-4 py-3 font-mono text-[11px] text-ink-muted">
                          {ev.source_id}
                        </td>
                        <td className="px-4 py-3">
                          <span className="px-2 py-0.5 rounded-pill bg-teal-500/10 text-teal-700 dark:text-teal-400 border border-teal-500/20 text-[10px] font-semibold">
                            {ev.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-ink-muted">
                          {new Date(ev.observed_at).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-3">
                          {ev.source_url ? (
                            <a
                              href={ev.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-lens hover:underline inline-flex items-center gap-1 font-mono text-[11px]"
                            >
                              <span>View Source</span>
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          ) : (
                            <span className="text-ink-muted italic">None</span>
                          )}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={7} className="px-4 py-6 text-center text-ink-muted italic">
                        No raw evidence items captured in this assessment.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 3: DECISION HISTORY */}
        {activeTab === "history" && (
          <div className="space-y-4">
            {finding.decision_history && finding.decision_history.length > 0 ? (
              <div className="space-y-3">
                {finding.decision_history.map((dh, idx) => (
                  <div
                    key={idx}
                    className="p-4 rounded-panel-nested bg-surface-2 border border-hairline space-y-2 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <StatusPill status={dh.status} />
                      <span className="text-ink-muted font-mono text-[11px]">
                        {new Date(dh.at).toLocaleString()}
                      </span>
                    </div>
                    {dh.reason && (
                      <p className="text-ink font-semibold">
                        Decision Reason: <span className="font-normal">{dh.reason}</span>
                      </p>
                    )}
                    {dh.notes && (
                      <p className="text-ink-muted text-[11px]">
                        Internal Notes: {dh.notes}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center text-xs text-ink-muted rounded-panel-nested bg-surface-2 border border-hairline">
                No previous analyst decisions recorded for this finding.
              </div>
            )}
          </div>
        )}
      </section>

      {/* Decision Dialog */}
      <DecisionDialog
        open={decisionOpen}
        onOpenChange={setDecisionOpen}
        finding={finding}
        initialStatus={finding.status}
      />
    </div>
  );
}
