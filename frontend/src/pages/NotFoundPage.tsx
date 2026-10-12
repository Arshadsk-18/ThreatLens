import React from "react";
import { Link } from "react-router-dom";
import { FileQuestion, ArrowLeft } from "lucide-react";

export function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
      <div className="w-16 h-16 rounded-pill bg-surface-2 border border-hairline flex items-center justify-center text-ink-muted mb-4 shadow-sm">
        <FileQuestion className="w-8 h-8 text-lens" aria-hidden="true" />
      </div>
      <h1 className="font-display font-bold text-2xl text-ink tracking-tight mb-2">
        404 — Route Not Located
      </h1>
      <p className="text-sm text-ink-muted max-w-md mb-6">
        The requested path does not exist in the ThreatLens section 15.1 route table or has been relocated.
      </p>
      <Link
        to="/"
        className="inline-flex items-center gap-2 px-4 py-2 rounded-pill bg-ink text-surface dark:bg-surface dark:text-ink text-xs font-semibold hover:opacity-90 transition-opacity focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lens"
      >
        <ArrowLeft className="w-4 h-4" />
        Return to Overview
      </Link>
    </div>
  );
}
