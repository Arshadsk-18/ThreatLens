import React, { useState, useEffect, Suspense } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { DemoBanner } from "@/components/cx/DemoBanner";
import { Skeleton } from "@/components/cx/Skeleton";
import { useBrand } from "@/context/useBrand";
import { ShieldCheck, Info } from "lucide-react";

function RouteLoadingFallback() {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-label="Loading page content"
      style={{
        padding: "1rem",
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

export function AppLayout() {
  const { isDemoBrand } = useBrand();
  const [collapsed, setCollapsed] = useState(false);
  const [isDark, setIsDark] = useState<boolean>(() => {
    return localStorage.getItem("threatlens-theme") === "dark";
  });

  useEffect(() => {
    if (isDark) {
      document.documentElement.setAttribute("data-theme", "dark");
      localStorage.setItem("threatlens-theme", "dark");
    } else {
      document.documentElement.removeAttribute("data-theme");
      localStorage.setItem("threatlens-theme", "light");
    }
  }, [isDark]);

  return (
    <div className="min-h-screen bg-canvas text-ink flex flex-col font-sans transition-colors">
      {/* Skip to main content accessibility link */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-3 focus:left-3 focus:z-50 focus:px-4 focus:py-2 focus:bg-ink focus:text-surface focus:rounded-pill focus:shadow-floating focus:outline-none focus:ring-2 focus:ring-lens text-xs font-semibold"
      >
        Skip to main content
      </a>

      {/* Persistent DemoBanner whenever current brand is demo_brand */}
      {isDemoBrand && <DemoBanner />}

      <div className="flex-1 flex w-full">
        {/* Left collapsible risk platform sidebar */}
        <Sidebar
          collapsed={collapsed}
          onToggleCollapse={() => setCollapsed((prev) => !prev)}
          isDark={isDark}
          onToggleTheme={() => setIsDark((prev) => !prev)}
        />

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0">
          <main id="main-content" className="flex-1 p-6 md:p-8" tabIndex={-1}>
            <Suspense fallback={<RouteLoadingFallback />}>
              <Outlet />
            </Suspense>
          </main>

          {/* Quiet Forensic Footer */}
          <footer className="border-t border-hairline bg-surface/50 py-4 px-6 md:px-8 text-xs text-ink-muted">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-lens shrink-0" aria-hidden="true" />
                <span>
                  <strong>ThreatLens</strong> v3.0.0 · Digital Risk Platform
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-center sm:text-right">
                <Info className="w-3.5 h-3.5 text-ink-muted shrink-0" aria-hidden="true" />
                <span>
                  Candidates for review. Scores are not probabilities. Official assets cleared by exact ID.
                </span>
              </div>
            </div>
          </footer>
        </div>
      </div>
    </div>
  );
}
