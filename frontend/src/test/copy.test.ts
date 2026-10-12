import { describe, it, expect } from 'vitest';
import {
  formatRiskScore,
  getFindingStatusLabel,
  sanitizeOrAssertCopy,
  formatSourceOutcomeMessage,
} from '../lib/copy';

describe('Copy rules compliance (ThreatLens v3 Contract §15.3 & §2)', () => {
  it('formats risk score with exact non-probability phrasing', () => {
    expect(formatRiskScore(72)).toBe('Risk score 72 / 100 (not a probability)');
    expect(formatRiskScore(null)).toBe('Insufficient evidence');
    expect(formatRiskScore(undefined)).toBe('Insufficient evidence');
  });

  it('never formats score as % chance or probability', () => {
    const formatted = formatRiskScore(85);
    expect(formatted).not.toContain('%');
    expect(formatted).not.toContain('chance');
    expect(formatted).not.toContain('accurate');
  });

  it('renders "Confirmed suspicious by analyst" only for CONFIRMED_SUSPICIOUS', () => {
    expect(getFindingStatusLabel('CONFIRMED_SUSPICIOUS')).toBe('Confirmed suspicious by analyst');
    expect(getFindingStatusLabel('NEW')).toBe('New candidate for review');
    expect(getFindingStatusLabel('IN_REVIEW')).toBe('In review');
  });

  it('strictly rejects forbidden accusation words unless analyst confirmed', () => {
    expect(() => sanitizeOrAssertCopy('This is a fake app')).toThrow(/Forbidden word "fake"/);
    expect(() => sanitizeOrAssertCopy('Likely phishing scheme')).toThrow(/Forbidden word "phishing"/);
    expect(() => sanitizeOrAssertCopy('Malicious developer')).toThrow(/Forbidden word "malicious"/);
    expect(() => sanitizeOrAssertCopy('High risk scam')).toThrow(/Forbidden word "scam"/);

    // Allowed when confirmed suspicious
    expect(sanitizeOrAssertCopy('Confirmed suspicious fake', true)).toBe('Confirmed suspicious fake');
  });

  it('formats source outcome states honestly and never hides not-connected', () => {
    const notConn = formatSourceOutcomeMessage({
      source_id: 'instagram',
      display_name: 'Instagram',
      status: 'NOT_CONNECTED',
    });
    expect(notConn).toContain('not connected');
    expect(notConn).toContain('Not queried');

    const rateLimited = formatSourceOutcomeMessage({
      source_id: 'bluesky_public',
      display_name: 'Bluesky Public',
      status: 'RATE_LIMITED',
      message: 'Stopped after 4 of 6 queries',
    });
    expect(rateLimited).toContain('rate limited');
    expect(rateLimited).toContain('Stopped after 4 of 6 queries');
  });
});
