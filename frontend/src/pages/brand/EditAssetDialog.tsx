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
import { AssetIcon } from "@/components/cx/AssetIcon";
import { Save, AlertCircle, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface EditAssetDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  brandId: string;
  asset: Schema["OfficialAsset"] | null;
}

export function EditAssetDialog({
  open,
  onOpenChange,
  brandId,
  asset,
}: EditAssetDialogProps) {
  const queryClient = useQueryClient();

  const [displayName, setDisplayName] = useState("");
  const [description, setDescription] = useState("");
  const [trustPublisher, setTrustPublisher] = useState(false);
  const [isActive, setIsActive] = useState(true);
  const [notes, setNotes] = useState("");

  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    if (asset) {
      setDisplayName(asset.display_name || "");
      setDescription(asset.description || "");
      setTrustPublisher(Boolean(asset.trust_publisher));
      setIsActive(Boolean(asset.is_active));
      setNotes(asset.notes || "");
      setErrorMessage(null);
      setSuccessMessage(null);
    }
  }, [asset]);

  const patchMutation = useMutation({
    mutationFn: async () => {
      if (!asset) return;
      setErrorMessage(null);
      return apiClient.patchAsset(brandId, asset.id, {
        display_name: displayName.trim(),
        description: description.trim(),
        trust_publisher: trustPublisher,
        is_active: isActive,
        notes: notes.trim(),
      });
    },
    onSuccess: () => {
      setSuccessMessage("Asset updated successfully.");
      queryClient.invalidateQueries({ queryKey: ["brand-assets", brandId] });
      queryClient.invalidateQueries({ queryKey: ["brand-summary", brandId] });
      setTimeout(() => {
        setSuccessMessage(null);
        onOpenChange(false);
      }, 700);
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Failed to update asset. Please check the values provided.");
      }
    },
  });

  if (!asset) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogHeader>
        <div className="flex items-center gap-3">
          <AssetIcon src={asset.icon_url || undefined} alt={asset.display_name} size="md" />
          <div>
            <DialogTitle>Edit Official Asset</DialogTitle>
            <DialogDescription>
              Update display metadata, trust parameters, and registry status.
            </DialogDescription>
          </div>
        </div>
      </DialogHeader>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          patchMutation.mutate();
        }}
        className="space-y-4"
      >
        {/* Read-only Immutable Identification Banner */}
        <div className="p-3 bg-surface-2 rounded-panel-nested border border-hairline space-y-1 text-xs">
          <div className="flex justify-between items-center text-ink-muted">
            <span>Platform: <strong className="text-ink font-mono">{asset.platform}</strong></span>
            <span>Relationship: <strong className="text-ink">{asset.relationship}</strong></span>
          </div>
          <div className="flex justify-between items-center text-ink-muted pt-1 border-t border-hairline/60">
            <span>Identifier: <code className="font-mono text-ink text-[11px]">{asset.stable_identifier}</code></span>
            <span>Method: <span className="font-mono text-ink text-[11px]">{asset.verification_method}</span></span>
          </div>
        </div>

        {errorMessage && (
          <div className="p-3 rounded-panel-nested bg-risk-critical/10 border border-risk-critical/30 text-risk-critical text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {successMessage && (
          <div className="p-3 rounded-panel-nested bg-emerald-500/10 border border-emerald-500/30 text-emerald-700 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{successMessage}</span>
          </div>
        )}

        <div className="space-y-1.5">
          <label htmlFor="edit-asset-display-name" className="text-xs font-semibold text-ink">
            Display Name
          </label>
          <input
            id="edit-asset-display-name"
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            required
            className="w-full px-3 py-2 text-xs rounded-panel-nested border border-hairline bg-surface text-ink focus:outline-none focus:ring-1 focus:ring-lens"
          />
        </div>

        <div className="space-y-1.5">
          <label htmlFor="edit-asset-desc" className="text-xs font-semibold text-ink">
            Description
          </label>
          <textarea
            id="edit-asset-desc"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            className="w-full px-3 py-2 text-xs rounded-panel-nested border border-hairline bg-surface text-ink focus:outline-none focus:ring-1 focus:ring-lens resize-none"
          />
        </div>

        <div className="grid grid-cols-2 gap-3 pt-1">
          <label className="flex items-center gap-2.5 p-3 rounded-panel-nested border border-hairline bg-surface-2 cursor-pointer hover:border-hairline/80 transition-colors">
            <input
              type="checkbox"
              checked={trustPublisher}
              onChange={(e) => setTrustPublisher(e.target.checked)}
              className="w-4 h-4 rounded text-lens focus:ring-lens"
            />
            <div className="text-xs">
              <span className="font-semibold text-ink block">Trust Publisher</span>
              <span className="text-[11px] text-ink-muted block">IdentityGuard R2 auto-clear</span>
            </div>
          </label>

          <label className="flex items-center gap-2.5 p-3 rounded-panel-nested border border-hairline bg-surface-2 cursor-pointer hover:border-hairline/80 transition-colors">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              className="w-4 h-4 rounded text-lens focus:ring-lens"
            />
            <div className="text-xs">
              <span className="font-semibold text-ink block">Active in Registry</span>
              <span className="text-[11px] text-ink-muted block">Queried during scans</span>
            </div>
          </label>
        </div>

        <div className="space-y-1.5">
          <label htmlFor="edit-asset-notes" className="text-xs font-semibold text-ink">
            Analyst Notes
          </label>
          <input
            id="edit-asset-notes"
            type="text"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="e.g. Verified via App Store Connect screenshot on 2026-10-12"
            className="w-full px-3 py-2 text-xs rounded-panel-nested border border-hairline bg-surface text-ink focus:outline-none focus:ring-1 focus:ring-lens"
          />
        </div>

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
            <span>{patchMutation.isPending ? "Saving..." : "Save Changes"}</span>
          </button>
        </div>
      </form>
    </Dialog>
  );
}
