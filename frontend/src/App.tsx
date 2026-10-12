import React, { Suspense, lazy } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrandProvider } from "@/context/BrandContext";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import { AppLayout } from "@/components/layout/AppLayout";
import { Skeleton } from "@/components/cx/Skeleton";

// Route-level code splitting
const OverviewPage = lazy(() => import("@/pages/OverviewPage").then(m => ({ default: m.OverviewPage })));
const BrandProfilePage = lazy(() => import("@/pages/BrandProfilePage").then(m => ({ default: m.BrandProfilePage })));
const ScanSetupPage = lazy(() => import("@/pages/ScanSetupPage").then(m => ({ default: m.ScanSetupPage })));
const ScanDetailPage = lazy(() => import("@/pages/ScanDetailPage").then(m => ({ default: m.ScanDetailPage })));
const FindingsQueuePage = lazy(() => import("@/pages/FindingsQueuePage").then(m => ({ default: m.FindingsQueuePage })));
const FindingDetailPage = lazy(() => import("@/pages/FindingDetailPage").then(m => ({ default: m.FindingDetailPage })));
const ClearedItemsPage = lazy(() => import("@/pages/ClearedItemsPage").then(m => ({ default: m.ClearedItemsPage })));
const SourceCoveragePage = lazy(() => import("@/pages/SourceCoveragePage").then(m => ({ default: m.SourceCoveragePage })));
const EvaluationLabPage = lazy(() => import("@/pages/EvaluationLabPage").then(m => ({ default: m.EvaluationLabPage })));
const EvidenceReportPage = lazy(() => import("@/pages/EvidenceReportPage").then(m => ({ default: m.EvidenceReportPage })));
const WelcomePage = lazy(() => import("@/pages/WelcomePage").then(m => ({ default: m.WelcomePage })));
const NotFoundPage = lazy(() => import("@/pages/NotFoundPage").then(m => ({ default: m.NotFoundPage })));

function RouteLoadingFallback() {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-label="Loading page content"
      style={{
        padding: "2rem",
        display: "flex",
        flexDirection: "column",
        gap: "1rem",
        maxWidth: 1200,
        margin: "0 auto",
      }}
    >
      <Skeleton style={{ height: "40px", width: "35%", borderRadius: "8px" }} />
      <Skeleton style={{ height: "140px", width: "100%", borderRadius: "8px" }} />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem" }}>
        <Skeleton style={{ height: "100px", borderRadius: "8px" }} />
        <Skeleton style={{ height: "100px", borderRadius: "8px" }} />
        <Skeleton style={{ height: "100px", borderRadius: "8px" }} />
      </div>
    </div>
  );
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000,
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrandProvider>
          <BrowserRouter>
            <Routes>
              {/* Standalone Landing Page outside app shell */}
              <Route
                path="/welcome"
                element={
                  <Suspense fallback={<RouteLoadingFallback />}>
                    <WelcomePage />
                  </Suspense>
                }
              />

              <Route element={<AppLayout />}>
                {/* Section 15.1 Route Table (nested under AppLayout Suspense) */}
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
          </BrowserRouter>
        </BrandProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
