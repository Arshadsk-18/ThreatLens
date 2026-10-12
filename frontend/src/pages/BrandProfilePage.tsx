import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import { ApiError } from "@/api/errors";
import { useBrand } from "@/context/useBrand";
import type { Schema } from "@/api/client";
import { BrandForm } from "./brand/BrandForm";
import { HowProfileIsUsed } from "./brand/HowProfileIsUsed";
import { AddAssetDialog } from "./brand/AddAssetDialog";
import { EditAssetDialog } from "./brand/EditAssetDialog";
import { AssetIcon } from "@/components/cx/AssetIcon";
import {
  Plus,
  ShieldCheck,
  ShieldAlert,
  Edit2,
  PowerOff,
  Power,
  Filter,
  CheckCircle2,
  ExternalLink,
  AlertTriangle,
} from "lucide-react";
import { cn } from "@/lib/utils";

export function BrandProfilePage() {
  const { activeBrand } = useBrand();
  const queryClient = useQueryClient();

  // Modals
  const [addAssetOpen, setAddAssetOpen] = useState(false);
  const [editingAsset, setEditingAsset] = useState<Schema["OfficialAsset"] | null>(null);

  // Filters
  const [filterType, setFilterType] = useState<string>("ALL");
  const [filterRelationship, setFilterRelationship] = useState<string>("ALL");
  const [filterVerified, setFilterVerified] = useState<string>("ALL");
  const [filterActive, setFilterActive] = useState<string>("ALL");

  // Query assets
  const {
    data: assetsData,
    isLoading: assetsLoading,
    isError: assetsError,
    error: assetsErr,
    refetch: refetchAssets,
  } = useQuery({
    queryKey: [
      "brand-assets",
      activeBrand?.id,
      filterType,
      filterRelationship,
      filterVerified,
      filterActive,
    ],
    queryFn: () => {
      if (!activeBrand) return null;
      return apiClient.getAssets(activeBrand.id, {
        asset_type: filterType === "ALL" ? undefined : (filterType as Schema["AssetType"]),
        relationship:
          filterRelationship === "ALL"
            ? undefined
            : (filterRelationship as Schema["Relationship"]),
        is_verified:
          filterVerified === "ALL" ? undefined : filterVerified === "VERIFIED",
        is_active:
          filterActive === "ALL" ? undefined : filterActive === "ACTIVE",
      });
    },
    enabled: !!activeBrand,
  });

  // Toggle active mutation
  const toggleActiveMutation = useMutation({
    mutationFn: async (asset: Schema["OfficialAsset"]) => {
      if (!activeBrand) return;
      return apiClient.patchAsset(activeBrand.id, asset.id, {
        is_active: !asset.is_active,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["brand-assets", activeBrand?.id] });
      queryClient.invalidateQueries({ queryKey: ["brand-summary", activeBrand?.id] });
    },
  });

  if (!activeBrand) {
    return (
      <div className="p-8 text-center text-ink-muted">
        No active brand selected. Please select a brand from the switcher.
      </div>
    );
  }

  const assets = assetsData?.items || [];

  return (
    <div className="space-y-8 animate-fade-in pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-hairline">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-display font-bold text-2xl text-ink tracking-tight">
              Brand Profile & Asset Registry
            </h1>
            {activeBrand.demo_brand && (
              <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-lens/10 text-lens font-semibold border border-lens/20">
                Demo Brand
              </span>
            )}
          </div>
          <p className="text-xs text-ink-muted mt-1">
            Ground-truth configuration driving query expansion, IdentityGuard auto-clear rules, and multi-signal candidate scoring.
          </p>
        </div>

        <button
          onClick={() => setAddAssetOpen(true)}
          className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-ink hover:bg-ink/90 rounded-pill shadow-sm transition-all shrink-0 self-start sm:self-center"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Register Official Asset</span>
        </button>
      </div>

      {/* Guided Context: How this profile is used */}
      <HowProfileIsUsed />

      {/* Brand Form */}
      <div className="rounded-panel border border-hairline bg-surface p-6 shadow-sm">
        <div className="mb-5 pb-3 border-b border-hairline">
          <h2 className="font-display font-semibold text-base text-ink tracking-tight">
            Brand Identification Parameters
          </h2>
          <p className="text-xs text-ink-muted mt-0.5">
            Configure validation tokens, authorized domain hostnames, and keywords used by the query planner.
          </p>
        </div>
        <BrandForm brand={activeBrand} />
      </div>

      {/* Assets Registry Table */}
      <div className="rounded-panel border border-hairline bg-surface shadow-sm overflow-hidden">
        <div className="p-6 border-b border-hairline flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-display font-semibold text-base text-ink tracking-tight">
                Official Assets Registry
              </h2>
              <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-surface-2 text-ink border border-hairline">
                {assetsData?.total ?? assets.length} registered
              </span>
            </div>
            <p className="text-xs text-ink-muted mt-0.5">
              Verified digital entities recognized by IdentityGuard. Never auto-verified from name match alone.
            </p>
          </div>

          <button
            onClick={() => setAddAssetOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-lens hover:bg-lens/5 rounded-pill border border-lens/30 transition-colors self-start md:self-auto"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Asset via Prefill</span>
          </button>
        </div>

        {/* Filters Bar */}
        <div className="bg-surface-2 px-6 py-3 border-b border-hairline flex flex-wrap items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5 text-ink-muted font-medium mr-1">
            <Filter className="w-3.5 h-3.5" />
            <span>Filters:</span>
          </div>

          {/* Asset Type */}
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-2.5 py-1 text-xs rounded-panel-nested border border-hairline bg-surface text-ink focus:outline-none focus:ring-1 focus:ring-lens"
          >
            <option value="ALL">All Types</option>
            <option value="IOS_APP">iOS App</option>
            <option value="ANDROID_APP">Android App</option>
            <option value="WEB_DOMAIN">Web Domain</option>
            <option value="SOCIAL_HANDLE">Social Handle</option>
          </select>

          {/* Relationship */}
          <select
            value={filterRelationship}
            onChange={(e) => setFilterRelationship(e.target.value)}
            className="px-2.5 py-1 text-xs rounded-panel-nested border border-hairline bg-surface text-ink focus:outline-none focus:ring-1 focus:ring-lens"
          >
            <option value="ALL">All Relationships</option>
            <option value="OFFICIAL">Official</option>
            <option value="SUBSIDIARY">Subsidiary</option>
            <option value="PARTNER">Partner</option>
            <option value="THIRD_PARTY_INTEGRATION">Third-Party Integration</option>
          </select>

          {/* Verification */}
          <select
            value={filterVerified}
            onChange={(e) => setFilterVerified(e.target.value)}
            className="px-2.5 py-1 text-xs rounded-panel-nested border border-hairline bg-surface text-ink focus:outline-none focus:ring-1 focus:ring-lens"
          >
            <option value="ALL">All Verification</option>
            <option value="VERIFIED">Verified</option>
            <option value="UNVERIFIED">Unverified</option>
          </select>

          {/* Active */}
          <select
            value={filterActive}
            onChange={(e) => setFilterActive(e.target.value)}
            className="px-2.5 py-1 text-xs rounded-panel-nested border border-hairline bg-surface text-ink focus:outline-none focus:ring-1 focus:ring-lens"
          >
            <option value="ALL">All Status</option>
            <option value="ACTIVE">Active Only</option>
            <option value="INACTIVE">Inactive Only</option>
          </select>

          {(filterType !== "ALL" ||
            filterRelationship !== "ALL" ||
            filterVerified !== "ALL" ||
            filterActive !== "ALL") && (
            <button
              onClick={() => {
                setFilterType("ALL");
                setFilterRelationship("ALL");
                setFilterVerified("ALL");
                setFilterActive("ALL");
              }}
              className="text-[11px] text-ink-muted hover:text-ink underline ml-auto"
            >
              Reset filters
            </button>
          )}
        </div>

        {/* Table Content */}
        {assetsError ? (
          <div className="p-8 text-center space-y-2">
            <AlertTriangle className="w-6 h-6 text-risk-critical mx-auto" />
            <h3 className="font-semibold text-xs text-ink">Failed to load brand assets</h3>
            <p className="text-xs text-ink-muted">
              {assetsErr instanceof ApiError ? assetsErr.message : "Error contacting API."}
            </p>
            {assetsErr instanceof ApiError && assetsErr.requestId && (
              <span className="font-mono text-[10px] text-ink-muted block">
                Request ID: {assetsErr.requestId}
              </span>
            )}
            <button
              onClick={() => refetchAssets()}
              className="mt-2 px-3 py-1.5 rounded-pill bg-ink text-white text-xs font-semibold hover:bg-ink/90 transition-colors"
            >
              Retry
            </button>
          </div>
        ) : assetsLoading ? (
          <div className="p-8 text-center text-xs text-ink-muted">Loading registered assets...</div>
        ) : assets.length === 0 ? (
          <div className="p-12 text-center space-y-2">
            <p className="text-xs font-semibold text-ink">No official assets found</p>
            <p className="text-xs text-ink-muted max-w-sm mx-auto">
              {filterType !== "ALL" || filterRelationship !== "ALL" || filterVerified !== "ALL" || filterActive !== "ALL"
                ? "No registered assets match your selected filter criteria."
                : "No official assets registered yet. Add apps, domains, or social handles to enable IdentityGuard."}
            </p>
            <button
              onClick={() => setAddAssetOpen(true)}
              className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-ink rounded-pill hover:bg-ink/90 transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Register First Asset</span>
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-surface-2 text-ink-muted border-b border-hairline text-[11px] font-medium">
                  <th className="py-2.5 px-4 w-10">Icon</th>
                  <th className="py-2.5 px-4">Display Name</th>
                  <th className="py-2.5 px-4">Platform</th>
                  <th className="py-2.5 px-4 font-mono">Stable Identifier</th>
                  <th className="py-2.5 px-4">Developer ID</th>
                  <th className="py-2.5 px-4">Relationship</th>
                  <th className="py-2.5 px-4">Verification Method</th>
                  <th className="py-2.5 px-4 text-center">Verified</th>
                  <th className="py-2.5 px-4 text-center">Trust Publisher</th>
                  <th className="py-2.5 px-4 text-center">Active</th>
                  <th className="py-2.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline">
                {assets.map((asset) => (
                  <tr
                    key={asset.id}
                    className={cn(
                      "hover:bg-surface-2/40 transition-colors",
                      !asset.is_active && "opacity-60 bg-surface-2/20"
                    )}
                  >
                    {/* Icon */}
                    <td className="py-3 px-4">
                      <AssetIcon
                        src={asset.icon_url || undefined}
                        alt={asset.display_name}
                        size="sm"
                      />
                    </td>

                    {/* Display Name */}
                    <td className="py-3 px-4">
                      <div className="font-semibold text-ink flex items-center gap-1.5">
                        <span>{asset.display_name}</span>
                        {asset.canonical_url && (
                          <a
                            href={asset.canonical_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-ink-muted hover:text-lens transition-colors"
                            title="Open canonical link"
                          >
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>
                      {asset.publisher_name && (
                        <div className="text-[11px] text-ink-muted truncate max-w-[180px]">
                          {asset.publisher_name}
                        </div>
                      )}
                    </td>

                    {/* Platform */}
                    <td className="py-3 px-4">
                      <span className="font-mono text-[11px] text-ink px-1.5 py-0.5 rounded bg-surface-2 border border-hairline">
                        {asset.platform}
                      </span>
                    </td>

                    {/* Stable Identifier */}
                    <td className="py-3 px-4">
                      <code className="font-mono text-[11px] text-ink bg-surface-2 px-1.5 py-0.5 rounded border border-hairline block truncate max-w-[140px]" title={asset.stable_identifier}>
                        {asset.stable_identifier}
                      </code>
                    </td>

                    {/* Developer ID */}
                    <td className="py-3 px-4">
                      <span className="font-mono text-[11px] text-ink-muted">
                        {asset.developer_id || asset.handle || "—"}
                      </span>
                    </td>

                    {/* Relationship */}
                    <td className="py-3 px-4">
                      <span
                        className={cn(
                          "px-2 py-0.5 rounded-full text-[10px] font-medium border",
                          asset.relationship === "OFFICIAL"
                            ? "bg-lens/10 text-lens border-lens/20"
                            : "bg-surface-2 text-ink-muted border-hairline"
                        )}
                      >
                        {asset.relationship}
                      </span>
                    </td>

                    {/* Verification Method */}
                    <td className="py-3 px-4">
                      <span className="text-[11px] font-mono text-ink-muted">
                        {asset.verification_method}
                      </span>
                    </td>

                    {/* Verified */}
                    <td className="py-3 px-4 text-center">
                      {asset.is_verified ? (
                        <span
                          className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200"
                          title="Identity verified by protocol or direct audit"
                        >
                          <CheckCircle2 className="w-3 h-3 shrink-0" />
                          <span>Verified</span>
                        </span>
                      ) : (
                        <span
                          className="inline-flex items-center gap-1 text-[11px] font-medium text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200"
                          title="Unverified asset. Rule R1/R2 requires verified identifiers."
                        >
                          <ShieldAlert className="w-3 h-3 shrink-0" />
                          <span>Unverified</span>
                        </span>
                      )}
                    </td>

                    {/* Trust Publisher */}
                    <td className="py-3 px-4 text-center">
                      {asset.trust_publisher ? (
                        <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-[#0E8F9C] bg-[#0E8F9C]/10 px-2 py-0.5 rounded-full border border-[#0E8F9C]/20">
                          <ShieldCheck className="w-3 h-3" />
                          <span>R2 Trusted</span>
                        </span>
                      ) : (
                        <span className="text-[11px] text-ink-muted font-mono">—</span>
                      )}
                    </td>

                    {/* Active */}
                    <td className="py-3 px-4 text-center">
                      <span
                        className={cn(
                          "px-2 py-0.5 rounded-full text-[10px] font-semibold",
                          asset.is_active
                            ? "bg-emerald-100/70 text-emerald-800"
                            : "bg-surface-2 text-ink-muted border border-hairline"
                        )}
                      >
                        {asset.is_active ? "ACTIVE" : "INACTIVE"}
                      </span>
                    </td>

                    {/* Actions */}
                    <td className="py-3 px-4 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => setEditingAsset(asset)}
                          className="p-1.5 text-ink-muted hover:text-ink hover:bg-surface-2 rounded-panel-nested transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-lens"
                          title="Edit asset details"
                          aria-label={`Edit ${asset.display_name} details`}
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>

                        <button
                          onClick={() => toggleActiveMutation.mutate(asset)}
                          disabled={toggleActiveMutation.isPending}
                          className={cn(
                            "p-1.5 rounded-panel-nested transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-lens",
                            asset.is_active
                              ? "text-ink-muted hover:text-risk-high hover:bg-risk-high/10"
                              : "text-ink-muted hover:text-emerald-700 hover:bg-emerald-50"
                          )}
                          title={asset.is_active ? "Deactivate asset" : "Activate asset"}
                          aria-label={asset.is_active ? `Deactivate ${asset.display_name}` : `Activate ${asset.display_name}`}
                        >
                          {asset.is_active ? (
                            <PowerOff className="w-3.5 h-3.5" />
                          ) : (
                            <Power className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add Asset Dialog */}
      <AddAssetDialog
        open={addAssetOpen}
        onOpenChange={setAddAssetOpen}
        brandId={activeBrand.id}
      />

      {/* Edit Asset Dialog */}
      <EditAssetDialog
        open={!!editingAsset}
        onOpenChange={(open) => !open && setEditingAsset(null)}
        brandId={activeBrand.id}
        asset={editingAsset}
      />
    </div>
  );
}
