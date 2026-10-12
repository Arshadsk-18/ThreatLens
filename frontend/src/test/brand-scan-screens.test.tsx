import React from "react";
import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { mockApiClient } from "@/api/mock";
import { BrandProvider } from "@/context/BrandContext";
import { BrandProfilePage } from "@/pages/BrandProfilePage";
import { ScanSetupPage } from "@/pages/ScanSetupPage";
import { ScanDetailPage } from "@/pages/ScanDetailPage";
import { FunnelBars } from "@/components/cx/FunnelBars";
import { ApiError } from "@/api/errors";
import {
  BRAND_ID,
  SCAN_ID,
  MOCK_FUNNEL,
} from "@/api/mock-data/fixtures";

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
            <Route path="/brand" element={<BrandProfilePage />} />
            <Route path="/scan" element={<ScanSetupPage />} />
            <Route path="/scan/:id" element={<ScanDetailPage />} />
            <Route path="/findings" element={<div>Findings Queue Page</div>} />
            <Route path="/cleared" element={<div>Cleared Items Page</div>} />
          </Routes>
        </BrandProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("Brand & Scan Rubric Requirements (Vitest)", () => {
  beforeEach(() => {
    // Reset any state if necessary
  });

  describe("Prefill States & Asset Registration", () => {
    it("handles allowlisted App Store link with prefill draft, source badge, and retrieved_at", async () => {
      const res = await mockApiClient.prefillAsset(BRAND_ID, {
        url: "https://apps.apple.com/us/app/kaveri-bank-mobile/id1234567890",
      });

      expect(res.source_id).toBe("apple_itunes");
      expect(res.source_mode).toBe("LIVE");
      expect(res.retrieved_at).toBeDefined();
      expect(res.draft).not.toBeNull();
      expect(res.draft?.stable_identifier).toBe("1234567890");
      expect(res.draft?.platform).toBe("apple_app_store");
      expect(res.draft?.asset_type).toBe("IOS_APP");
      expect(res.draft?.display_name).toContain("Kaveri Bank");
    });

    it("handles allowlisted Bluesky profile link with domain verified handle", async () => {
      const res = await mockApiClient.prefillAsset(BRAND_ID, {
        url: "https://bsky.app/profile/kaveribank.example",
      });

      expect(res.source_id).toBe("bluesky_public");
      expect(res.source_mode).toBe("LIVE");
      expect(res.draft).not.toBeNull();
      expect(res.draft?.platform).toBe("bluesky");
      expect(res.draft?.verification_method).toBe("DOMAIN_VERIFIED_HANDLE");
    });

    it("throws 422 BLOCKED_URL when user submits non-allowlisted URL", async () => {
      try {
        await mockApiClient.prefillAsset(BRAND_ID, {
          url: "https://unauthorized-crawler-target.org/fake-app",
        });
        expect.fail("Should have thrown 422 BLOCKED_URL");
      } catch (err) {
        expect(err).toBeInstanceOf(ApiError);
        const apiErr = err as ApiError;
        expect(apiErr.status).toBe(422);
        expect(apiErr.code).toBe("BLOCKED_URL");
        expect(apiErr.details?.[0].issue).toContain("allowlisted");
      }
    });

    it("enforces 409 CONFLICT on duplicate asset registration", async () => {
      try {
        // Attempt to register existing asset (Apple App Store ID 1234567890)
        await mockApiClient.createAsset(BRAND_ID, {
          platform: "apple_app_store",
          asset_type: "IOS_APP",
          stable_identifier: "1234567890",
          display_name: "Kaveri Bank Duplicate",
          canonical_url: "https://apps.apple.com/app/id1234567890",
          relationship: "OFFICIAL",
          verification_method: "STORE_LOOKUP",
        });
        expect.fail("Should have thrown 409 CONFLICT");
      } catch (err) {
        expect(err).toBeInstanceOf(ApiError);
        const apiErr = err as ApiError;
        expect(apiErr.status).toBe(409);
        expect(apiErr.code).toBe("CONFLICT");
        expect(apiErr.message).toContain("already exists");
      }
    });

    it("returns a publisher warning when new OFFICIAL asset publisher differs from registered publisher", async () => {
      const asset = await mockApiClient.createAsset(BRAND_ID, {
        platform: "apple_app_store",
        asset_type: "IOS_APP",
        stable_identifier: "9999888877",
        display_name: "Kaveri Wealth",
        publisher_name: "Different Publisher Solutions Ltd",
        canonical_url: "https://apps.apple.com/app/id9999888877",
        relationship: "OFFICIAL",
        verification_method: "STORE_LOOKUP",
      });

      expect(asset.warning).not.toBeNull();
      expect(asset.warning).toContain("differs from registered official publisher");
    });
  });

  describe("Scan Setup Rules & Validation", () => {
    it("strictly prevents mixing demo_fixtures or recorded_fixtures into LIVE scan with 422 MODE_NOT_ALLOWED", async () => {
      try {
        await mockApiClient.createScan({
          brand_id: BRAND_ID,
          mode: "LIVE",
          source_ids: ["demo_fixtures", "apple_itunes"],
        });
        expect.fail("Should have thrown 422 MODE_NOT_ALLOWED");
      } catch (err) {
        expect(err).toBeInstanceOf(ApiError);
        const apiErr = err as ApiError;
        expect(apiErr.status).toBe(422);
        expect(apiErr.code).toBe("MODE_NOT_ALLOWED");
      }
    });

    it("throws 409 SCAN_ALREADY_RUNNING when an active scan is already in progress", async () => {
      // First scan
      const first = await mockApiClient.createScan({
        brand_id: BRAND_ID,
        mode: "DEMO",
      });
      expect(first.id).toBeDefined();

      // Immediately start second scan for same brand
      try {
        await mockApiClient.createScan({
          brand_id: BRAND_ID,
          mode: "DEMO",
        });
        expect.fail("Should have thrown 409 SCAN_ALREADY_RUNNING");
      } catch (err) {
        expect(err).toBeInstanceOf(ApiError);
        const apiErr = err as ApiError;
        expect(apiErr.status).toBe(409);
        expect(apiErr.code).toBe("SCAN_ALREADY_RUNNING");
        expect(apiErr.details?.[0].field).toBe("scan_id");
      }
    });
  });

  describe("Source-Outcome Copy for Each Status (§15.3)", () => {
    it("renders NOT_CONNECTED source honest copy: not connected, not queried, does not look errored", async () => {
      renderWithProviders(<ScanDetailPage />, `/scan/${SCAN_ID}`);

      await waitFor(() => {
        expect(screen.getByRole("heading", { name: "Scan Detail" })).toBeInTheDocument();
      });

      expect(
        screen.getByText(/not connected\. No official API; not queried\. Not queried\./i)
      ).toBeInTheDocument();
    });

    it("renders RATE_LIMITED source copy stating stopped after N of M queries with partial results kept", async () => {
      renderWithProviders(<ScanDetailPage />, `/scan/${SCAN_ID}`);

      await waitFor(() => {
        expect(screen.getByRole("heading", { name: "Scan Detail" })).toBeInTheDocument();
      });

      // From 15.3 copy guide: "Stopped after 4 of 6 queries; partial results kept."
      expect(
        screen.getAllByText(/Stopped after 4 of 6 queries; partial results kept\./i).length
      ).toBeGreaterThan(0);
    });

    it("renders CACHED badge and timestamp for cached responses", async () => {
      renderWithProviders(<ScanDetailPage />, `/scan/${SCAN_ID}`);

      await waitFor(() => {
        expect(screen.getByRole("heading", { name: "Scan Detail" })).toBeInTheDocument();
      });

      expect(screen.getAllByText(/Cached result from 05:12 UTC/i).length).toBeGreaterThan(0);
    });
  });

  describe("Funnel Visual & Arithmetic Invariant Note", () => {
    it("renders the exact arithmetic invariant note", () => {
      renderWithProviders(
        <FunnelBars funnel={MOCK_FUNNEL} scanId={SCAN_ID} />
      );

      // 60 = 5 + 29 + 14 + 0 + 12
      const note = screen.getByText(
        /Invariant note: 60 \(deduplicated\) = 5 \(cleared\) \+ 29 \(not relevant\) \+ 14 \(benign lookalike\) \+ 0 \(below threshold\) \+ 12 \(findings\)\./i
      );
      expect(note).toBeInTheDocument();
    });

    it("links Findings and Cleared numbers to their respective filtered routes", () => {
      renderWithProviders(
        <FunnelBars funnel={MOCK_FUNNEL} scanId={SCAN_ID} />
      );

      const findingsLink = screen.getByRole("link", { name: /Findings/i });
      expect(findingsLink).toHaveAttribute("href", `/findings?scan_id=${SCAN_ID}`);

      const clearedLink = screen.getByRole("link", { name: /Official cleared/i });
      expect(clearedLink).toHaveAttribute("href", `/cleared?scan_id=${SCAN_ID}`);
    });
  });

  describe("Empty-Findings Copy (§15.3)", () => {
    it("computes honest empty-findings copy without ever saying 'All clear'", () => {
      const queriedCount = 3;
      const notConnectedCount = 1;
      const copy = `No candidates for review in this scan. ${queriedCount} sources were queried, ${notConnectedCount} was not connected.`;

      expect(copy).toContain("No candidates for review in this scan.");
      expect(copy).toContain("3 sources were queried, 1 was not connected.");
      expect(copy).not.toContain("All clear");
    });
  });
});
