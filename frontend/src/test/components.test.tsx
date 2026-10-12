import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import {
  SourceBadge,
  SeverityPill,
  StatusPill,
  RiskScore,
  CoverageMeter,
  NameDiff,
  AssetIcon,
  EmptyState,
  ErrorState,
  NotConnectedState,
  DemoBanner,
  StatTile,
  Gauge,
  FunnelBars,
  DataTable,
  DataTableHeader,
  DataTableBody,
  DataTableRow,
  DataTableHead,
  DataTableCell,
  Dialog,
  DialogTitle,
} from '@/components/cx';
import { App } from '@/App';

describe('Forensic Lens CX Primitives & Design Direction', () => {
  describe('SourceBadge (Cool ramp & text for every SourceMode / SourceStatus)', () => {
    // SourceMode values: LIVE, CACHED, SIMULATED
    it('renders LIVE with text "Live" and dot icon', () => {
      render(<SourceBadge status="LIVE" />);
      expect(screen.getByText('Live')).toBeInTheDocument();
    });

    it('renders CACHED with text containing timestamp format', () => {
      render(<SourceBadge status="CACHED" cacheTime="14:30 UTC" />);
      expect(screen.getByText('Cached result from 14:30 UTC')).toBeInTheDocument();
    });

    it('renders SIMULATED with text "Simulated" and dashed border', () => {
      const { container } = render(<SourceBadge status="SIMULATED" />);
      expect(screen.getByText('Simulated')).toBeInTheDocument();
      const badge = container.querySelector('span');
      expect(badge).toHaveClass('border-dashed');
    });

    // SourceStatus values: CONNECTED, PARTIAL, NOT_CONNECTED, RATE_LIMITED, ERROR
    it('renders CONNECTED with text "Connected"', () => {
      render(<SourceBadge status="CONNECTED" />);
      expect(screen.getByText('Connected')).toBeInTheDocument();
    });

    it('renders PARTIAL with text "Partial"', () => {
      render(<SourceBadge status="PARTIAL" />);
      expect(screen.getByText('Partial')).toBeInTheDocument();
    });

    it('renders NOT_CONNECTED with text "Not connected" and hollow plug icon', () => {
      render(<SourceBadge status="NOT_CONNECTED" />);
      expect(screen.getByText('Not connected')).toBeInTheDocument();
    });

    it('renders RATE_LIMITED with text "Rate limited" and ink background', () => {
      const { container } = render(<SourceBadge status="RATE_LIMITED" />);
      expect(screen.getByText('Rate limited')).toBeInTheDocument();
      const badge = container.querySelector('span');
      expect(badge).toHaveClass('bg-ink');
    });

    it('renders ERROR with text "Source error" and ink background', () => {
      const { container } = render(<SourceBadge status="ERROR" />);
      expect(screen.getByText('Source error')).toBeInTheDocument();
      const badge = container.querySelector('span');
      expect(badge).toHaveClass('bg-ink');
    });
  });

  describe('SeverityPill (Warm ramp & never renders colour without text)', () => {
    it('renders Low with text "Low"', () => {
      const { container } = render(<SeverityPill severity="LOW" />);
      expect(screen.getByText('Low')).toBeInTheDocument();
      expect(container.textContent).toContain('Low');
    });

    it('renders Medium with text "Medium"', () => {
      const { container } = render(<SeverityPill severity="MEDIUM" />);
      expect(screen.getByText('Medium')).toBeInTheDocument();
      expect(container.textContent).toContain('Medium');
    });

    it('renders High with text "High"', () => {
      const { container } = render(<SeverityPill severity="HIGH" />);
      expect(screen.getByText('High')).toBeInTheDocument();
      expect(container.textContent).toContain('High');
    });

    it('renders Critical with text "Critical"', () => {
      const { container } = render(<SeverityPill severity="CRITICAL" />);
      expect(screen.getByText('Critical')).toBeInTheDocument();
      expect(container.textContent).toContain('Critical');
    });

    it('verifies SeverityPill never renders color alone across all severities', () => {
      const severities = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'] as const;
      for (const sev of severities) {
        const { container } = render(<SeverityPill severity={sev} />);
        const text = container.textContent?.trim();
        expect(text).toBeTruthy();
        expect(['Low', 'Medium', 'High', 'Critical']).toContain(text);
      }
    });
  });

  describe('RiskScore (Strict non-probability phrasing)', () => {
    it('strictly outputs "Risk score 72 / 100 (not a probability)"', () => {
      render(<RiskScore score={72} />);
      expect(screen.getByText('Risk score')).toBeInTheDocument();
      expect(screen.getByText('72')).toBeInTheDocument();
      expect(screen.getByText('/ 100')).toBeInTheDocument();
      expect(screen.getByText('(not a probability)')).toBeInTheDocument();
    });

    it('renders Insufficient evidence when score is null', () => {
      render(<RiskScore score={null} />);
      expect(screen.getByText('Insufficient evidence')).toBeInTheDocument();
    });
  });

  describe('NameDiff (Signature character-by-character idea with Cyrillic U+0456 codepoint chip)', () => {
    it('highlights changed segments with underline and bold (non-colour cue)', () => {
      render(
        <NameDiff
          official="Kaveri Bank"
          candidate="Kaveri Bank Rewards"
          diffSegments={[
            { text: 'Kaveri Bank', changed: false },
            { text: ' Rewards', changed: true },
          ]}
        />
      );
      const changedSeg = screen.getByText('Rewards');
      expect(changedSeg).toHaveClass('underline');
      expect(changedSeg).toHaveClass('font-bold');
    });

    it('marks Cyrillic U+0456 with a codepoint chip and a non-colour cue', () => {
      // Cyrillic small letter by U+0456
      const homoglyphCandidate = 'kaver\u0456bank';
      render(<NameDiff official="kaveribank" candidate={homoglyphCandidate} />);

      // Assert codepoint chip
      expect(screen.getByText('U+0456')).toBeInTheDocument();
      expect(screen.getByText('Non-ASCII Characters & Homoglyphs Detected')).toBeInTheDocument();

      // Assert non-colour cue (index label chip '(pos 5)' and character tape with index number)
      expect(screen.getByText('(pos 5)')).toBeInTheDocument();
    });
  });

  describe('AssetIcon, CoverageMeter, StatTile, Gauge, FunnelBars, DataTable, Dialog', () => {
    it('renders AssetIcon with fallback monogram when src is missing', () => {
      render(<AssetIcon alt="Kaveri Bank" />);
      expect(screen.getByText('K')).toBeInTheDocument();
    });

    it('renders CoverageMeter with percentage and G3 threshold notice', () => {
      render(<CoverageMeter coverage={0.4} />);
      expect(screen.getByText('40%')).toBeInTheDocument();
      expect(screen.getByText(/G3 cap/)).toBeInTheDocument();
    });

    it('renders StatTile with big number and quiet label', () => {
      render(<StatTile label="Candidates for review" value="6" hint="Signals observed" />);
      expect(screen.getByText('Candidates for review')).toBeInTheDocument();
      expect(screen.getByText('6')).toBeInTheDocument();
    });

    it('renders Gauge semicircle with score and label', () => {
      render(<Gauge value={72} label="Headline risk score" />);
      expect(screen.getByText('72')).toBeInTheDocument();
      expect(screen.getByText('Headline risk score')).toBeInTheDocument();
    });

    it('renders FunnelBars and confirms mathematical invariant', () => {
      const funnel = {
        retrieved: 64,
        deduplicated: 60,
        official_cleared: 5,
        not_relevant: 29,
        benign_lookalike: 14,
        below_threshold: 0,
        findings: 12,
      };
      render(<FunnelBars funnel={funnel} />);
      expect(screen.getByText('Invariant satisfied: 100% accounted for')).toBeInTheDocument();
    });

    it('renders DataTable with structured rows and cells', () => {
      render(
        <DataTable>
          <DataTableHeader>
            <DataTableRow>
              <DataTableHead>Name</DataTableHead>
              <DataTableHead>Score</DataTableHead>
            </DataTableRow>
          </DataTableHeader>
          <DataTableBody>
            <DataTableRow>
              <DataTableCell>Test Finding</DataTableCell>
              <DataTableCell>72</DataTableCell>
            </DataTableRow>
          </DataTableBody>
        </DataTable>
      );
      expect(screen.getByText('Test Finding')).toBeInTheDocument();
      expect(screen.getByText('72')).toBeInTheDocument();
    });

    it('renders Dialog modal when open', () => {
      render(
        <Dialog open={true} onOpenChange={() => {}}>
          <DialogTitle>Confirm Decision</DialogTitle>
          <div>Dialog Content</div>
        </Dialog>
      );
      expect(screen.getByText('Confirm Decision')).toBeInTheDocument();
      expect(screen.getByText('Dialog Content')).toBeInTheDocument();
    });
  });

  describe('EmptyState, ErrorState, NotConnectedState, DemoBanner, StatusPill', () => {
    it('renders DemoBanner with persistent contract copy', () => {
      render(<DemoBanner />);
      expect(screen.getByText('Demo data. Simulated records are labelled.')).toBeInTheDocument();
    });

    it('renders NotConnectedState with platform name', () => {
      render(<NotConnectedState platform="Instagram" />);
      expect(screen.getByText('Instagram: not connected')).toBeInTheDocument();
    });

    it('renders StatusPill with exact contract copy', () => {
      render(<StatusPill status="CONFIRMED_SUSPICIOUS" />);
      expect(screen.getByText('Confirmed suspicious by analyst')).toBeInTheDocument();
    });

    it('renders EmptyState and ErrorState', () => {
      render(<EmptyState title="Nothing here" description="Zero records present" />);
      expect(screen.getByText('Nothing here')).toBeInTheDocument();

      render(<ErrorState title="Failed request" message="Network error" requestId="req-123" />);
      expect(screen.getByText('Failed request')).toBeInTheDocument();
      expect(screen.getByText(/req-123/)).toBeInTheDocument();
    });
  });

  describe('App Shell rendering & Route Table Section 15.1', () => {
    it('renders the complete forensic workspace shell on mock client with brand switcher and demo banner', async () => {
      render(<App />);
      expect(screen.getAllByText('ThreatLens')[0]).toBeInTheDocument();
      expect(screen.getByText('Demo data. Simulated records are labelled.')).toBeInTheDocument();
      await waitFor(() => {
        expect(screen.getAllByText('Kaveri Bank')[0]).toBeInTheDocument();
      });
      expect(screen.getAllByText('Overview')[0]).toBeInTheDocument();
    });
  });
});
