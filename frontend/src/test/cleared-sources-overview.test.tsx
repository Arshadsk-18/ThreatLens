import React from "react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { apiClient } from "@/api/client";
import { BrandProvider } from "@/context/BrandContext";
import { ClearedItemsPage } from "@/pages/ClearedItemsPage";
import { SourceCoveragePage } from "@/pages/SourceCoveragePage";
import { OverviewPage } from "@/pages/OverviewPage";
import { BRAND_ID } from "@/api/mock-data/fixtures";

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
        <BrandProvider>
          <Routes>
            <Route path="/" element={ui} />
            <Route path="/cleared" element={<ClearedItemsPage />} />
            <Route path="/sources" element={<SourceCoveragePage />} />
            <Route path="/overview" element={<OverviewPage />} />
          </Routes>
        </BrandProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("/cleared, /sources, and / (Overview) Screens", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe("Cleared Assets Page (/cleared)", () => {
    it("renders R2, G4, and G5 exact 15.3 copy and badges", async () => {
      renderWithProviders(<ClearedItemsPage />, "/cleared");

      await waitFor(() => {
        expect(
          screen.getByRole("heading", { name: "Cleared Assets Registry" })
        ).toBeInTheDocument();
      });

      // Verify R2 copy
      await waitFor(() => {
        expect(
          screen.getByText("Published by the registered developer. Consider registering this app.")
        ).toBeInTheDocument();
      });

      // Verify G4 copy
      const g4Elements = screen.getAllByText(
        "Similar name, unrelated category, no corroborating evidence."
      );
      expect(g4Elements.length).toBeGreaterThanOrEqual(1);

      // Verify G5 copy
      expect(
        screen.getByText(
          "Declared unofficial in its bio. Not verified. Disclaimers can be copied by impersonators; an analyst may reopen this."
        )
      ).toBeInTheDocument();

      // Verify G5 badge
      expect(
        screen.getByText("Declared unofficial, not verified")
      ).toBeInTheDocument();

      // Verify score capped explanation for G4/G5
      const scoreCappedElements = screen.getAllByText(
        /\(score capped: G4\/G5 prevents candidate reaching alert threshold\)/i
      );
      expect(scoreCappedElements.length).toBeGreaterThanOrEqual(1);

      // Verify disabled P1 reopen button
      const reopenButtons = screen.getAllByRole("button", { name: /Reopen \(P1\)/i });
      expect(reopenButtons.length).toBeGreaterThan(0);
      expect(reopenButtons[0]).toBeDisabled();
    });

    it("never writes 'Safe' or 'Legitimate' without the rule", async () => {
      renderWithProviders(<ClearedItemsPage />, "/cleared");

      await waitFor(() => {
        expect(
          screen.getByRole("heading", { name: "Cleared Assets Registry" })
        ).toBeInTheDocument();
      });

      // Assert no standalone "Safe" or "Legitimate" labels exist
      expect(screen.queryByText(/^Safe$/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/^Legitimate$/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/Status: Safe/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/Status: Legitimate/i)).not.toBeInTheDocument();
    });
  });

  describe("Source Coverage Page (/sources)", () => {
    it("renders required entries from 11.1, NOT_CONNECTED messages, and legend with last outcome note", async () => {
      renderWithProviders(<SourceCoveragePage />, "/sources");

      await waitFor(() => {
        expect(
          screen.getByRole("heading", { name: /Source Coverage & Provider Health/i })
        ).toBeInTheDocument();
      });

      // Verify legend entries
      expect(screen.getByText("Source Modes & Status Legend")).toBeInTheDocument();
      expect(
        screen.getByText(/Status reflects the last real outcome\./i)
      ).toBeInTheDocument();
      expect(screen.getByText("LIVE")).toBeInTheDocument();
      expect(screen.getByText("CACHED")).toBeInTheDocument();
      expect(screen.getByText("SIMULATED")).toBeInTheDocument();
      expect(screen.getByText("NOT_CONNECTED")).toBeInTheDocument();
      expect(screen.getByText("RATE_LIMITED / ERROR")).toBeInTheDocument();

      // Verify connected sources
      await waitFor(() => {
        expect(screen.getByText("Apple App Store search")).toBeInTheDocument();
      });
      expect(screen.getByText("Bluesky Public Directory")).toBeInTheDocument();

      // Verify NOT_CONNECTED sources and their exact messages
      expect(screen.getByText("Bluesky Post Search")).toBeInTheDocument();
      expect(screen.getByText("Requires authenticated session.")).toBeInTheDocument();

      expect(screen.getByText("Google Play Catalog")).toBeInTheDocument();
      expect(screen.getByText("No official API; not queried.")).toBeInTheDocument();

      expect(screen.getByText("Instagram Graph API")).toBeInTheDocument();
      const platformAccessElements = screen.getAllByText("Requires platform API access.");
      expect(platformAccessElements.length).toBeGreaterThanOrEqual(1);

      // Verify "Check now" button is present
      expect(screen.getByRole("button", { name: /Check now/i })).toBeInTheDocument();
    });
  });

  describe("Overview Dashboard (/)", () => {
    it("renders greeting banner with brand name, KPI tiles, FunnelBars, and Review progress gauge", async () => {
      renderWithProviders(<OverviewPage />, "/");

      await waitFor(() => {
        expect(
          screen.getByText(/Good (morning|afternoon|evening), Kaveri Bank/i)
        ).toBeInTheDocument();
      });

      // Verify Primary action "Start scan"
      expect(screen.getByRole("link", { name: /Start scan/i })).toBeInTheDocument();

      // Verify KPI Tiles
      expect(screen.getByText("Candidates for review")).toBeInTheDocument();
      expect(screen.getByText("Cleared by rules")).toBeInTheDocument();
      expect(screen.getByText("Official assets registered")).toBeInTheDocument();
      expect(screen.getByText("Last Scan")).toBeInTheDocument();

      // Verify FunnelBars presence
      const funnelHeadings = screen.getAllByText("Detection & Filtering Funnel");
      expect(funnelHeadings.length).toBeGreaterThanOrEqual(1);

      // Verify Review progress label (never risk percentage)
      expect(screen.getByText("Review progress")).toBeInTheDocument();
      expect(screen.queryByText(/Risk percentage/i)).not.toBeInTheDocument();

      // Verify Source Coverage Strip
      expect(screen.getByText("Source Coverage Strip")).toBeInTheDocument();
      expect(screen.getByText("apple_itunes")).toBeInTheDocument();

      // Verify Latest Evaluation card
      expect(screen.getByText("Latest Evaluation")).toBeInTheDocument();
      expect(screen.getByText("Precision")).toBeInTheDocument();
      expect(screen.getByText("Recall")).toBeInTheDocument();
    });

    it("renders guided empty state when brand has 0 official assets and no scans", async () => {
      const spy = vi.spyOn(apiClient, "getBrandSummary").mockResolvedValue({
        brand_id: BRAND_ID,
        official_asset_count: 0,
        last_scan: null,
        funnel: {
          retrieved: 0,
          deduplicated: 0,
          official_cleared: 0,
          not_relevant: 0,
          benign_lookalike: 0,
          below_threshold: 0,
          findings: 0,
        },
        findings_by_severity: { LOW: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 0 },
        findings_by_status: {
          NEW: 0,
          IN_REVIEW: 0,
          CONFIRMED_SUSPICIOUS: 0,
          DISMISSED_FALSE_POSITIVE: 0,
          INCONCLUSIVE: 0,
        },
        findings_by_platform: {},
        cleared_by_decision: {
          OFFICIAL_EXACT_MATCH: 0,
          OFFICIAL_PUBLISHER_MATCH: 0,
          AUTHORIZED_PARTNER_MATCH: 0,
          BENIGN_LOOKALIKE: 0,
          BELOW_THRESHOLD: 0,
          CANDIDATE_FOR_REVIEW: 0,
        },
        review_progress: { reviewed: 0, total: 0 },
        source_coverage: [],
        latest_evaluation: null,
      });

      renderWithProviders(<OverviewPage />, "/");

      await waitFor(() => {
        expect(
          screen.getByText(/Register an official asset, then run a scan/i)
        ).toBeInTheDocument();
      });

      expect(screen.getByText("Welcome to ThreatLens")).toBeInTheDocument();
      expect(
        screen.getByRole("link", { name: /Add Official Asset/i })
      ).toBeInTheDocument();

      spy.mockRestore();
    });
  });
});
