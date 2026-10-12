import React from "react";
import { useParams } from "react-router-dom";
import { RoutePlaceholder } from "@/components/common/RoutePlaceholder";
import { FileText } from "lucide-react";

export function EvidenceReportPage() {
  const { id } = useParams<{ id: string }>();

  return (
    <RoutePlaceholder
      title="Evidence Report Package"
      route={`/report/${id || ":id"}`}
      endpoints={["GET /findings/{id}/report"]}
      description="P1 endpoint: JSON forensic evidence export and audit documentation package."
      dataPreview={
        <div className="p-4 rounded-panel-nested bg-surface-2 border border-hairline flex items-center gap-3">
          <FileText className="w-5 h-5 text-lens shrink-0" aria-hidden="true" />
          <div className="text-xs">
            <span className="font-semibold text-ink block">
              P1 Feature Placeholder — Evidence Dossier
            </span>
            <span className="text-ink-muted">
              Report generation endpoint reserved per Section 11.7. Ready for implementation.
            </span>
          </div>
        </div>
      }
    />
  );
}
