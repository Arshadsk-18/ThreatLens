import React, { useState, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import { ApiError } from "@/api/errors";
import type { Schema } from "@/api/client";
import {
  Dialog,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/cx/Dialog";
import { StatusPill } from "@/components/cx/StatusPill";
import { SeverityPill } from "@/components/cx/SeverityPill";
import { AlertCircle, Save } from "lucide-react";
import { cn } from "@/lib/utils";

interface DecisionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  finding: {
    id: string;
    candidate: {
      display_name: string;
      platform: string;
      handle?: string | null;
    };
    risk_score: number;
    severity: Schema["Severity"];
    status: Schema["FindingStatus"];
  } | null;
  initialStatus?: Schema["FindingStatus"];
  onSuccess?: () => void;
}

export function DecisionDialog({
  open,
  onOpenChange,
  finding,
  initialStatus,
  onSuccess,
}: DecisionDialogProps) {
  const queryClient = useQueryClient();

  const [status, setStatus] = useState<Schema["FindingStatus"]>(
    initialStatus || finding?.status || "IN_REVIEW"
  );
  const [decisionReason, setDecisionReason] = useState("");
  const [notes, setNotes] = useState("");

  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (finding) {
      setStatus(initialStatus || finding.status || "IN_REVIEW");
      setDecisionReason("");
      setNotes("");
      setErrorMessage(null);
      setValidationError(null);
    }
  }, [finding, initialStatus, open]);

  // Check if reason is required per contract rules
  const isReasonRequired =
    status === "DISMISSED_FALSE_POSITIVE" ||
    status === "CONFIRMED_SUSPICIOUS" ||
    status === "INCONCLUSIVE";

  const patchMutation = useMutation({
    mutationFn: async () => {
      if (!finding) return;
      setErrorMessage(null);
      setValidationError(null);

      // Client validation: decision_reason required for CONFIRMED_SUSPICIOUS, DISMISSED_FALSE_POSITIVE, INCONCLUSIVE
      if (isReasonRequired && (!decisionReason || decisionReason.trim() === "")) {
        setValidationError(
          `A decision reason is mandatory when setting status to ${status.replace(/_/g, " ")}.`
        );
        throw new Error("Validation failed");
      }

      return apiClient.patchFinding(finding.id, {
        status,
        decision_reason: decisionReason.trim() || undefined,
        notes: notes.trim() || undefined,
      });
    },
    onMutate: async () => {
      if (!finding) return;
      // Optimistic update
      await queryClient.cancelQueries({ queryKey: ["finding", finding.id] });
      const previousFinding = queryClient.getQueryData(["finding", finding.id]);
      if (previousFinding) {
        queryClient.setQueryData<Schema["FindingDetail"]>(["finding", finding.id], (old) =>
          old ? { ...old, status } : old
        );
      }
      return { previousFinding };
    },
    onError: (err: unknown, _vars, context) => {
      if (finding && context?.previousFinding) {
        queryClient.setQueryData(["finding", finding.id], context.previousFinding);
      }
      if (err instanceof ApiError) {
        if (err.status === 422 && err.details?.[0]?.issue) {
          setErrorMessage(err.details[0].issue);
        } else {
          setErrorMessage(err.message);
        }
      } else if (err instanceof Error && err.message !== "Validation failed") {
        setErrorMessage("Failed to record decision. Please verify fields.");
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["findings"] });
      if (finding) {
        queryClient.invalidateQueries({ queryKey: ["finding", finding.id] });
        queryClient.refetchQueries({ queryKey: ["finding", finding.id] });
      }
      queryClient.invalidateQueries({ queryKey: ["brand-summary"] });
      queryClient.invalidateQueries({ queryKey: ["audit"] });

      if (onSuccess) onSuccess();
      onOpenChange(false);
    },
  });

  if (!finding) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogHeader>
        <div className="flex items-start justify-between">
          <div>
            <DialogTitle>Record Analyst Decision</DialogTitle>
            <DialogDescription>
              Record an audit-logged decision for candidate{" "}
              <strong className="text-ink">{finding.candidate.display_name}</strong>.
            </DialogDescription>
          </div>
          <SeverityPill severity={finding.severity} />
        </div>
      </DialogHeader>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          patchMutation.mutate();
        }}
        className="space-y-4"
      >
        {/* Candidate Context Strip */}
        <div className="p-3 bg-surface-2 rounded-panel-nested border border-hairline flex items-center justify-between text-xs">
          <div>
            <span className="text-ink font-semibold block">{finding.candidate.display_name}</span>
            <span className="font-mono text-[11px] text-ink-muted">
              Platform: {finding.candidate.platform} · Risk score: {finding.risk_score}/100
            </span>
          </div>
          <div className="text-right">
            <span className="text-[10px] text-ink-muted block">Current Status</span>
            <StatusPill status={finding.status} />
          </div>
        </div>

        {/* Errors */}
        {(errorMessage || validationError) && (
          <div className="p-3 rounded-panel-nested bg-risk-critical/10 border border-risk-critical/30 text-risk-critical text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{validationError || errorMessage}</span>
          </div>
        )}

        {/* Status Selection */}
        <div className="space-y-2">
          <label className="text-xs font-semibold text-ink uppercase tracking-wider block">
            Target Status
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {[
              {
                id: "NEW" as Schema["FindingStatus"],
                label: "New",
                desc: "Reset candidate to unreviewed queue",
              },
              {
                id: "IN_REVIEW" as Schema["FindingStatus"],
                label: "In Review",
                desc: "Analyst is actively evaluating evidence",
              },
              {
                id: "CONFIRMED_SUSPICIOUS" as Schema["FindingStatus"],
                label: "Confirmed Suspicious",
                desc: "Confirmed suspicious by analyst (triggers takedown flow)",
              },
              {
                id: "DISMISSED_FALSE_POSITIVE" as Schema["FindingStatus"],
                label: "Dismissed (False Positive)",
                desc: "Candidate is a benign namesake or harmless variant",
              },
              {
                id: "INCONCLUSIVE" as Schema["FindingStatus"],
                label: "Inconclusive",
                desc: "Insufficient observable evidence to resolve",
              },
            ].map((opt) => (
              <label
                key={opt.id}
                onClick={() => {
                  setStatus(opt.id);
                  setValidationError(null);
                }}
                className={cn(
                  "p-3 rounded-panel-nested border cursor-pointer transition-all text-xs flex flex-col justify-between",
                  status === opt.id
                    ? "bg-surface border-lens shadow-xs ring-1 ring-lens/20"
                    : "bg-surface-2 border-hairline hover:border-hairline/80"
                )}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold text-ink">{opt.label}</span>
                  <input
                    type="radio"
                    name="finding-status"
                    checked={status === opt.id}
                    onChange={() => setStatus(opt.id)}
                    className="accent-lens"
                  />
                </div>
                <span className="text-[11px] text-ink-muted leading-tight">{opt.desc}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Reason Field */}
        <div className="space-y-1.5">
          <label htmlFor="decision-reason" className="text-xs font-semibold text-ink flex items-center justify-between">
            <span>
              Decision Reason {isReasonRequired && <span className="text-risk-critical">*</span>}
            </span>
            {isReasonRequired ? (
              <span className="text-[10px] text-risk-critical font-medium">
                Mandatory for this status
              </span>
            ) : (
              <span className="text-[10px] text-ink-muted">Optional</span>
            )}
          </label>
          <textarea
            id="decision-reason"
            value={decisionReason}
            onChange={(e) => {
              setDecisionReason(e.target.value);
              if (validationError) setValidationError(null);
            }}
            rows={2}
            placeholder={
              status === "CONFIRMED_SUSPICIOUS"
                ? "e.g., Confirmed unauthorized use of logo with synthetic Cyrillic homoglyph in banking category."
                : status === "DISMISSED_FALSE_POSITIVE"
                ? "e.g., Verified legitimate independent software vendor operating in unrelated domain."
                : "Enter explanation for decision audit log..."
            }
            className={cn(
              "w-full px-3 py-2 text-xs rounded-panel-nested border bg-surface text-ink focus:outline-none focus:ring-1 focus:ring-lens resize-none",
              validationError ? "border-risk-critical bg-risk-critical/5" : "border-hairline"
            )}
          />
        </div>

        {/* Optional Notes */}
        <div className="space-y-1.5">
          <label htmlFor="decision-notes" className="text-xs font-semibold text-ink">
            Internal Notes (Optional)
          </label>
          <input
            id="decision-notes"
            type="text"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="e.g. Case ref #DRP-2026-904"
            className="w-full px-3 py-2 text-xs rounded-panel-nested border border-hairline bg-surface text-ink focus:outline-none focus:ring-1 focus:ring-lens"
          />
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end gap-2 pt-3 border-t border-hairline">
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            className="px-3.5 py-1.5 text-xs font-medium text-ink-muted hover:text-ink transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={patchMutation.isPending}
            className={cn(
              "px-4 py-1.5 text-xs font-semibold text-white bg-ink rounded-pill flex items-center gap-1.5 shadow-sm hover:bg-ink/90 transition-all",
              patchMutation.isPending && "opacity-50 cursor-not-allowed"
            )}
          >
            <Save className="w-3.5 h-3.5" />
            <span>{patchMutation.isPending ? "Recording..." : "Save Decision"}</span>
          </button>
        </div>
      </form>
    </Dialog>
  );
}
