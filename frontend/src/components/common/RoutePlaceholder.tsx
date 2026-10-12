import React from "react";
import { Layers } from "lucide-react";

interface RoutePlaceholderProps {
  title: string;
  route: string;
  endpoints: string[];
  description: string;
  dataPreview?: React.ReactNode;
}

export function RoutePlaceholder({
  title,
  route,
  endpoints,
  description,
  dataPreview,
}: RoutePlaceholderProps) {
  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-hairline pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <h1 className="font-display font-bold text-2xl text-ink tracking-tight">
              {title}
            </h1>
            <span className="font-mono text-xs px-2.5 py-0.5 rounded-pill bg-surface-2 text-ink-muted border border-hairline font-semibold">
              {route}
            </span>
          </div>
          <p className="text-sm text-ink-muted">{description}</p>
        </div>
      </div>

      <div className="bg-surface rounded-panel-nested border border-hairline p-6 shadow-sm space-y-4">
        <div className="flex items-center gap-2 text-xs font-semibold text-ink-muted uppercase tracking-wider">
          <Layers className="w-4 h-4 text-lens" aria-hidden="true" />
          <span>Section 15.1 Contract Endpoints</span>
        </div>

        <div className="flex flex-wrap gap-2">
          {endpoints.map((ep) => (
            <span
              key={ep}
              className="font-mono text-xs px-3 py-1 rounded-pill bg-surface-2 text-ink border border-hairline font-medium"
            >
              {ep}
            </span>
          ))}
        </div>

        {dataPreview && (
          <div className="pt-4 border-t border-hairline">
            <div className="text-xs font-semibold text-ink-muted mb-3 uppercase tracking-wider">
              Connected Mock Client Live State
            </div>
            {dataPreview}
          </div>
        )}
      </div>
    </div>
  );
}
