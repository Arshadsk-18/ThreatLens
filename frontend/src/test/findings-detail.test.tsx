import React from "react";
import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { mockApiClient } from "@/api/mock";
import { BrandProvider } from "@/context/BrandContext";
import { FindingDetailPage } from "@/pages/FindingDetailPage";
import { FindingsQueuePage } from "@/pages/FindingsQueuePage";
import { DecisionDialog } from "@/pages/findings/DecisionDialog";
import { MOCK_FINDINGS } from "@/api/mock-data/fixtures";

function renderWithProviders(ui: React.ReactElement, initialRoute = "/") {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialRoute]}>
        <BrandProvider client={mockApiClient}>
          <Routes>
            <Route path="/" element={ui} />
            <Route path="/findings" element={<FindingsQueuePage />} />
            <Route path="/findings/:id" element={<FindingDetailPage />} />
          </Routes>
        </BrandProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("Findings Queue and Detail Rubric Requirements (Vitest)", () => {
  beforeEach(() => {
    // Clean state
  });

  describe("72 / HIGH Finding Detail & Exact Points Sum", () => {
    it("renders Kaveri Bank Rewards with risk score 72 and signals sum to 72 points", async () => {
      const findingId = "f1000000-0000-0000-0000-000000000001";
      const finding = MOCK_FINDINGS.find((f) => f.id === findingId)!;
      expect(finding).toBeDefined();
      expect(finding.risk_score).toBe(72);
      expect(finding.severity).toBe("HIGH");

      // Verify mathematical points sum from score breakdown
      const sumPoints = finding.score_breakdown.reduce((acc, curr) => acc + curr.points, 0);
      expect(Math.round(sumPoints)).toBe(72);

      renderWithProviders(<FindingDetailPage />, `/findings/${findingId}`);

      // Verify Header and Non-probability phrasing
      await waitFor(() => {
        expect(screen.getByText("Kaveri Bank Rewards")).toBeInTheDocument();
      });

      expect(
        screen.getByText("Risk score 72 / 100 (not a probability)")
      ).toBeInTheDocument();

      // Verify "How this score was built" section
      expect(screen.getByText("How this score was built")).toBeInTheDocument();
      expect(screen.getByText("Total: 72 pts")).toBeInTheDocument();

      // Verify corroborating groups line
      expect(
        screen.getByText(/Corroborating groups: Visual, Content, Context\. The name group never counts as corroboration\./i)
      ).toBeInTheDocument();

      // Verify Evidence Compare tab is active by default with forensic dimensions
      await waitFor(() => {
        expect(screen.getByText("Forensic Dimension")).toBeInTheDocument();
      });
      expect(
        screen.getByText(/Icon perceptual hash is 93% similar\. Hash similarity is not proof of copying\./i)
      ).toBeInTheDocument();

      // Verify neutral publisher difference styling
      expect(screen.getByText("Publisher difference recorded as observable fact.")).toBeInTheDocument();
    });
  });

  describe("Capped 49 Example & Coverage Warning", () => {
    it("renders finding 7 capped at 49 with coverage note 'Insufficient evidence: only the name could be observed.'", async () => {
      const findingId = "f1000000-0000-0000-0000-000000000007";
      const finding = MOCK_FINDINGS.find((f) => f.id === findingId)!;
      expect(finding).toBeDefined();
      expect(finding.risk_score).toBe(49);
      expect(finding.gates_applied).toContain("G2");
      expect(finding.gates_applied).toContain("G3");
      expect(finding.evidence_coverage).toBeLessThan(0.5);

      renderWithProviders(<FindingDetailPage />, `/findings/${findingId}`);

      await waitFor(() => {
        expect(screen.getByText("Risk score 49 / 100 (not a probability)")).toBeInTheDocument();
      });

      // Verify Gates applied card shows score capped at 49 and coverage warning
      expect(screen.getByText("Score capped at 49")).toBeInTheDocument();
      const coverageNotes = screen.getAllByText("Insufficient evidence: only the name could be observed.");
      expect(coverageNotes.length).toBeGreaterThanOrEqual(1);
    });
  });

  describe("Homoglyph Chip with Cyrillic U+0456", () => {
    it("renders homoglyph chip and plain sentence on finding 5", async () => {
      const findingId = "f1000000-0000-0000-0000-000000000005";
      renderWithProviders(<FindingDetailPage />, `/findings/${findingId}`);

      await waitFor(() => {
        // Look for the codepoint chip
        expect(screen.getByText("U+0456")).toBeInTheDocument();
      });

      // Look for the plain sentence describing the homoglyph
      expect(
        screen.getByText(/Contains 1 non-ASCII character: і \(U\+0456\)/i)
      ).toBeInTheDocument();
    });
  });

  describe("SIMULATED Badge on Fixture Finding", () => {
    it("renders SIMULATED badge on simulated finding 3", async () => {
      const findingId = "f1000000-0000-0000-0000-000000000003";
      renderWithProviders(<FindingDetailPage />, `/findings/${findingId}`);

      await waitFor(() => {
        expect(screen.getByText("Kaveri Bank Instant Loan")).toBeInTheDocument();
      });

      // Check for SIMULATED badge in header and breakdown
      const simulatedBadges = screen.getAllByText("SIMULATED");
      expect(simulatedBadges.length).toBeGreaterThan(0);
    });
  });

  describe("Decision Dialog Validation", () => {
    it("enforces mandatory decision_reason on Dismissal and Confirmation", async () => {
      const finding = MOCK_FINDINGS[0];

      render(
        <QueryClientProvider client={new QueryClient()}>
          <DecisionDialog
            open={true}
            onOpenChange={() => {}}
            finding={finding}
            initialStatus="DISMISSED_FALSE_POSITIVE"
          />
        </QueryClientProvider>
      );

      // Attempt to submit without reason
      const saveBtn = screen.getByRole("button", { name: /save decision/i });
      fireEvent.click(saveBtn);

      // Verify validation error
      await waitFor(() => {
        expect(
          screen.getByText(/A decision reason is mandatory when setting status to DISMISSED FALSE POSITIVE/i)
        ).toBeInTheDocument();
      });

      // Type a reason and verify error clears
      const reasonInput = screen.getByPlaceholderText(/e\.g\., Verified legitimate independent software vendor/i);
      fireEvent.change(reasonInput, {
        target: { value: "Legitimate third-party rewards partner verified manually." },
      });

      expect(
        screen.queryByText(/A decision reason is mandatory when setting status to DISMISSED FALSE POSITIVE/i)
      ).not.toBeInTheDocument();
    });
  });
});
