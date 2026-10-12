import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrandProvider } from "@/context/BrandContext";
import { AppLayout } from "@/components/layout/AppLayout";
import { OverviewPage } from "@/pages/OverviewPage";
import { BrandProfilePage } from "@/pages/BrandProfilePage";
import { ScanSetupPage } from "@/pages/ScanSetupPage";
import { ScanDetailPage } from "@/pages/ScanDetailPage";
import { FindingsQueuePage } from "@/pages/FindingsQueuePage";
import { FindingDetailPage } from "@/pages/FindingDetailPage";
import { ClearedItemsPage } from "@/pages/ClearedItemsPage";
import { SourceCoveragePage } from "@/pages/SourceCoveragePage";
import { EvaluationLabPage } from "@/pages/EvaluationLabPage";
import { EvidenceReportPage } from "@/pages/EvidenceReportPage";
import { NotFoundPage } from "@/pages/NotFoundPage";

function renderWithShell(initialRoute: string) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <BrandProvider>
        <MemoryRouter initialEntries={[initialRoute]}>
          <Routes>
            <Route element={<AppLayout />}>
              <Route path="/" element={<OverviewPage />} />
              <Route path="/brand" element={<BrandProfilePage />} />
              <Route path="/scan" element={<ScanSetupPage />} />
              <Route path="/scan/:id" element={<ScanDetailPage />} />
              <Route path="/findings" element={<FindingsQueuePage />} />
              <Route path="/findings/:id" element={<FindingDetailPage />} />
              <Route path="/cleared" element={<ClearedItemsPage />} />
              <Route path="/sources" element={<SourceCoveragePage />} />
              <Route path="/evaluation" element={<EvaluationLabPage />} />
              <Route path="/report/:id" element={<EvidenceReportPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
        </MemoryRouter>
      </BrandProvider>
    </QueryClientProvider>
  );
}

describe("Section 15.1 Route Table & Shell Placeholder Renders", () => {
  it("renders Overview placeholder inside shell on /", async () => {
    renderWithShell("/");
    expect(screen.getAllByText("ThreatLens")[0]).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /Kaveri Bank|Overview/i })).toBeInTheDocument();
    });
  });

  it("renders Brand Profile placeholder inside shell on /brand", async () => {
    renderWithShell("/brand");
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Brand Profile & Asset Registry" })).toBeInTheDocument();
    });
  });

  it("renders Scan Setup placeholder inside shell on /scan", async () => {
    renderWithShell("/scan");
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Scan Setup & History" })).toBeInTheDocument();
    });
  });

  it("renders Scan Detail placeholder inside shell on /scan/:id", async () => {
    renderWithShell("/scan/s2000000-0000-0000-0000-000000000001");
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Scan Detail" })).toBeInTheDocument();
    });
  });

  it("renders Findings Queue inside shell on /findings", async () => {
    renderWithShell("/findings");
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /Findings/i })).toBeInTheDocument();
    });
  });

  it("renders Finding Detail inside shell on /findings/:id", async () => {
    renderWithShell("/findings/f1000000-0000-0000-0000-000000000001");
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Kaveri Bank Rewards" })).toBeInTheDocument();
    });
  });

  it("renders Cleared Items placeholder inside shell on /cleared", async () => {
    renderWithShell("/cleared");
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /Cleared Assets/i })).toBeInTheDocument();
    });
  });

  it("renders Source Coverage placeholder inside shell on /sources", async () => {
    renderWithShell("/sources");
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /Source Coverage/i })).toBeInTheDocument();
    });
  });

  it("renders Evaluation Lab placeholder inside shell on /evaluation", async () => {
    renderWithShell("/evaluation");
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Evaluation Lab" })).toBeInTheDocument();
    });
  });

  it("renders Evidence Report P1 placeholder inside shell on /report/:id", async () => {
    renderWithShell("/report/rep-sample-01");
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Evidence Report Package" })).toBeInTheDocument();
    });
  });

  it("renders NotFound 404 page inside shell on undefined route", async () => {
    renderWithShell("/non-existent-route-404");
    await waitFor(() => {
      expect(screen.getByText("404 — Route Not Located")).toBeInTheDocument();
    });
  });
});
