import React from "react";
import { Shield, Search, SlidersHorizontal, Info } from "lucide-react";

export function HowProfileIsUsed() {
  return (
    <div className="rounded-panel-nested border border-hairline bg-surface p-5 space-y-4 shadow-sm">
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-lens/10 text-lens flex items-center justify-center shrink-0">
          <Info className="w-4 h-4" aria-hidden="true" />
        </div>
        <div>
          <h2 className="font-display font-semibold text-sm text-ink tracking-tight">
            How This Profile Drives Detection
          </h2>
          <p className="text-xs text-ink-muted">
            Official assets form the ground truth for ThreatLens. Identity is established by verified identifiers, never by name similarity.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1">
        <div className="p-3.5 rounded-panel-nested bg-surface-2 border border-hairline space-y-1.5">
          <div className="flex items-center gap-2 text-xs font-semibold text-ink">
            <Search className="w-3.5 h-3.5 text-lens shrink-0" aria-hidden="true" />
            <span>1. Query Planning</span>
          </div>
          <p className="text-[11px] text-ink-muted leading-relaxed">
            Brand name, distinctive tokens (<code className="font-mono text-ink">kaveri</code>), and keywords generate up to 8 Apple and 6 Bluesky queries to maximize candidate recall.
          </p>
        </div>

        <div className="p-3.5 rounded-panel-nested bg-surface-2 border border-hairline space-y-1.5">
          <div className="flex items-center gap-2 text-xs font-semibold text-ink">
            <Shield className="w-3.5 h-3.5 text-[#0E8F9C] shrink-0" aria-hidden="true" />
            <span>2. IdentityGuard</span>
          </div>
          <p className="text-[11px] text-ink-muted leading-relaxed">
            Registered assets are cleared by exact bundle ID (<code className="font-mono text-ink">R1</code>), developer ID (<code className="font-mono text-ink">R2</code>), or authorized partner ID (<code className="font-mono text-ink">R3</code>).
          </p>
        </div>

        <div className="p-3.5 rounded-panel-nested bg-surface-2 border border-hairline space-y-1.5">
          <div className="flex items-center gap-2 text-xs font-semibold text-ink">
            <SlidersHorizontal className="w-3.5 h-3.5 text-[#D9480F] shrink-0" aria-hidden="true" />
            <span>3. Multi-Signal Scoring</span>
          </div>
          <p className="text-[11px] text-ink-muted leading-relaxed">
            Unmatched candidates are compared against official assets across 7 observable signals. Fired evidence groups and gates (G1–G5) determine review necessity.
          </p>
        </div>
      </div>

      <div className="p-2.5 rounded-lg bg-surface-2/60 border border-hairline text-[11px] text-ink-muted flex items-start gap-2">
        <span className="font-semibold text-ink shrink-0">Forensic Principle:</span>
        <span>
          ThreatLens surfaces candidates for review, never proven fraud. Registration does not guarantee immunity; every observed candidate is evaluated deterministically against stored evidence.
        </span>
      </div>
    </div>
  );
}
