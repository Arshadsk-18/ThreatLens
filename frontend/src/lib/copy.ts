/**
 * ThreatLens v3 UI Copy and Language Compliance Utilities
 * Enforces non-negotiable principles from ARCHITECTURE_API_CONTRACT.md:
 * - Candidates for review, never accusations.
 * - Words "fake", "scam", "malicious", "phishing" are STRICTLY forbidden unless status is CONFIRMED_SUSPICIOUS.
 * - Scores are formatted as "Risk score X / 100 (not a probability)", never "% chance".
 * - A failed source is a failure, never "0 results".
 * - Not-connected sources are acknowledged, never hidden.
 */

export const FORBIDDEN_WORDS = ['fake', 'scam', 'malicious', 'phishing'] as const;

export function formatRiskScore(score: number | null | undefined): string {
  if (score === null || score === undefined) {
    return 'Insufficient evidence';
  }
  return `Risk score ${Math.round(score)} / 100 (not a probability)`;
}

export function formatSeverityLabel(severity: string | null | undefined): string {
  if (!severity) return 'UNRATED';
  return severity.toUpperCase();
}

export function getFindingStatusLabel(status: string): string {
  switch (status) {
    case 'CONFIRMED_SUSPICIOUS':
      return 'Confirmed suspicious by analyst';
    case 'NEW':
      return 'New candidate for review';
    case 'IN_REVIEW':
      return 'In review';
    case 'DISMISSED_FALSE_POSITIVE':
      return 'Dismissed (false positive)';
    case 'INCONCLUSIVE':
      return 'Inconclusive';
    default:
      return status;
  }
}

export function sanitizeOrAssertCopy(text: string, isConfirmedSuspicious = false): string {
  if (isConfirmedSuspicious) return text;

  const lower = text.toLowerCase();
  for (const word of FORBIDDEN_WORDS) {
    if (new RegExp(`\\b${word}\\b`, 'i').test(lower)) {
      throw new Error(
        `Contract Violation: Forbidden word "${word}" found in UI text: "${text}". ` +
        `Forbidden words may only appear when finding status is CONFIRMED_SUSPICIOUS.`
      );
    }
  }
  return text;
}

export function formatSourceOutcomeMessage(source: {
  display_name?: string;
  source_id: string;
  status: string;
  candidate_count?: number;
  message?: string | null;
}): string {
  const name = source.display_name || source.source_id;
  if (source.status === 'NOT_CONNECTED') {
    return `${name}: not connected. Requires platform API access. Not queried.`;
  }
  if (source.status === 'ERROR') {
    return `${name}: error encountered. Query failed (${source.message || 'Provider unavailable'}).`;
  }
  if (source.status === 'RATE_LIMITED') {
    return `${name}: rate limited. ${source.message || 'Partial results kept.'}`;
  }
  if (source.status === 'PARTIAL') {
    return `${name}: partial results. ${source.message || 'Some queries failed.'}`;
  }
  if (source.status === 'CONNECTED') {
    return `${name}: connected. ${source.candidate_count ?? 0} candidates observed.`;
  }
  return `${name}: ${source.status}`;
}

export const EMPTY_STATE_COPY = {
  FINDINGS: 'No candidates for review in this scan. All queried sources completed evaluation.',
  CLEARED: 'No cleared assets recorded for this query.',
  SCANS: 'No scans recorded yet. Launch a LIVE or DEMO scan to begin monitoring.',
  NOT_CONNECTED_HELP: 'Not-connected sources cannot be queried in LIVE mode without registered provider credentials.',
};
