import React, { useState } from "react";
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
import { SourceBadge } from "@/components/cx/SourceBadge";
import {
  Search,
  Sparkles,
  AlertTriangle,
  AlertCircle,
  Plus,
  CheckCircle2,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface AddAssetDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  brandId: string;
}

export function AddAssetDialog({
  open,
  onOpenChange,
  brandId,
}: AddAssetDialogProps) {
  const queryClient = useQueryClient();

  // Step state: 'PREFILL' | 'FORM'
  const [step, setStep] = useState<"PREFILL" | "FORM">("PREFILL");

  // Prefill inputs
  const [prefillUrl, setPrefillUrl] = useState("");
  const [prefillPlatform, setPrefillPlatform] = useState("apple_app_store");
  const [prefillIdentifier, setPrefillIdentifier] = useState("");
  const [prefillMode, setPrefillMode] = useState<"URL" | "ID">("URL");

  // Prefill feedback
  const [prefillNotice, setPrefillNotice] = useState<{
    source_id: string;
    source_mode: Schema["SourceMode"];
    retrieved_at: string;
  } | null>(null);
  const [prefillError, setPrefillError] = useState<string | null>(null);
  const [prefillEmptyNotice, setPrefillEmptyNotice] = useState<string | null>(null);

  // Form Fields
  const [assetType, setAssetType] = useState<Schema["AssetType"]>("IOS_APP");
  const [platform, setPlatform] = useState("apple_app_store");
  const [stableIdentifier, setStableIdentifier] = useState("");
  const [bundleId, setBundleId] = useState("");
  const [developerId, setDeveloperId] = useState("");
  const [publisherName, setPublisherName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [handle, setHandle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("Finance");
  const [canonicalUrl, setCanonicalUrl] = useState("");
  const [iconUrl, setIconUrl] = useState("");
  const [relationship, setRelationship] = useState<Schema["Relationship"]>("OFFICIAL");
  const [verificationMethod, setVerificationMethod] =
    useState<Schema["VerificationMethod"]>("STORE_LOOKUP");
  const [isVerified, setIsVerified] = useState(false);
  const [trustPublisher, setTrustPublisher] = useState(true);
  const [notes, setNotes] = useState("");

  // Submit Feedback
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitWarning, setSubmitWarning] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Prefill Mutation
  const prefillMutation = useMutation({
    mutationFn: async () => {
      setPrefillError(null);
      setPrefillEmptyNotice(null);

      const requestPayload: Schema["PrefillRequest"] =
        prefillMode === "URL"
          ? ({ url: prefillUrl.trim() } as Schema["PrefillRequest"])
          : ({
              platform: prefillPlatform,
              identifier: prefillIdentifier.trim(),
            } as Schema["PrefillRequest"]);

      return apiClient.prefillAsset(brandId, requestPayload);
    },
    onSuccess: (data) => {
      if (data.draft) {
        const d = data.draft;
        setAssetType(d.asset_type);
        setPlatform(d.platform);
        setStableIdentifier(d.stable_identifier);
        setBundleId(d.secondary_identifiers?.bundle_id || "");
        setDeveloperId(d.developer_id || "");
        setPublisherName(d.publisher_name || "");
        setDisplayName(d.display_name);
        setDescription(d.description || "");
        setCategory(d.category || "Finance");
        setCanonicalUrl(d.canonical_url);
        setIconUrl(d.icon_url || "");
        setRelationship(d.relationship || "OFFICIAL");
        setVerificationMethod(d.verification_method || "STORE_LOOKUP");
        setTrustPublisher(d.trust_publisher ?? true);
        setIsVerified(false); // Contract rule: Never auto-set is_verified from name match

        setPrefillNotice({
          source_id: data.source_id,
          source_mode: data.source_mode,
          retrieved_at: data.retrieved_at,
        });
        setStep("FORM");
      } else {
        // draft: null scenario
        setPrefillEmptyNotice(
          data.message ||
            `Provider lookup returned no draft (${data.source_status || "NOT_CONNECTED"}: ${data.error_code || "PROVIDER_UNAVAILABLE"}). You can enter details manually below.`
        );
      }
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError && err.status === 422) {
        const blockedDetail = err.details?.find((d) => d.issue?.includes("BLOCKED_URL"));
        if (blockedDetail) {
          setPrefillError(
            "Blocked URL: Host is not allowlisted. Only apps.apple.com and bsky.app profile URLs are permitted. You may continue with manual entry."
          );
        } else {
          setPrefillError(err.message || "Invalid prefill request pattern.");
        }
      } else if (err instanceof ApiError) {
        setPrefillError(`Lookup error (${err.code}): ${err.message}`);
      } else {
        setPrefillError("Failed to communicate with provider catalog.");
      }
    },
  });

  // Create Mutation
  const createMutation = useMutation({
    mutationFn: async () => {
      setSubmitError(null);
      setSubmitWarning(null);

      const secondary_identifiers: Record<string, string> = {};
      if (bundleId.trim()) {
        secondary_identifiers.bundle_id = bundleId.trim();
      }

      return apiClient.createAsset(brandId, {
        asset_type: assetType,
        platform,
        stable_identifier: stableIdentifier.trim(),
        secondary_identifiers,
        developer_id: developerId.trim() || null,
        publisher_name: publisherName.trim() || null,
        display_name: displayName.trim(),
        handle: handle.trim() || null,
        description: description.trim(),
        category: category.trim(),
        canonical_url: canonicalUrl.trim(),
        icon_url: iconUrl.trim() || null,
        relationship,
        verification_method: verificationMethod,
        is_verified: isVerified,
        trust_publisher: trustPublisher,
        notes: notes.trim(),
      });
    },
    onSuccess: (newAsset) => {
      if (newAsset.warning) {
        setSubmitWarning(newAsset.warning);
      }
      setSuccess(true);
      queryClient.invalidateQueries({ queryKey: ["brand-assets", brandId] });
      queryClient.invalidateQueries({ queryKey: ["brand-summary", brandId] });
      setTimeout(() => {
        handleReset();
        onOpenChange(false);
      }, 1500);
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError && err.status === 409) {
        setSubmitError(
          `Conflict: An official asset with platform '${platform}' and identifier '${stableIdentifier}' already exists for this brand.`
        );
      } else if (err instanceof ApiError && err.status === 422) {
        setSubmitError(err.message || "Validation failed for asset fields.");
      } else if (err instanceof ApiError) {
        setSubmitError(`Error (${err.code}): ${err.message}`);
      } else {
        setSubmitError("Failed to register official asset.");
      }
    },
  });

  const handleReset = () => {
    setStep("PREFILL");
    setPrefillUrl("");
    setPrefillIdentifier("");
    setPrefillNotice(null);
    setPrefillError(null);
    setPrefillEmptyNotice(null);
    setStableIdentifier("");
    setDisplayName("");
    setPublisherName("");
    setDeveloperId("");
    setBundleId("");
    setSubmitError(null);
    setSubmitWarning(null);
    setSuccess(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <div className="space-y-4 max-h-[85vh] overflow-y-auto pr-1">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-lens/10 text-lens flex items-center justify-center shrink-0">
              <Plus className="w-4 h-4" aria-hidden="true" />
            </div>
            <DialogTitle>Register Official Asset</DialogTitle>
          </div>
          <DialogDescription>
            Official assets define the ground truth for IdentityGuard. Official assets are excluded by exact identity evidence, never by name similarity.
          </DialogDescription>
        </DialogHeader>

        {/* Global Warnings / Success */}
        {submitError && (
          <div className="p-3 rounded-panel-nested bg-[#A4123F]/10 border border-[#A4123F]/25 text-[#A4123F] dark:text-[#FEB2B2] text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
            <span>{submitError}</span>
          </div>
        )}

        {submitWarning && (
          <div className="p-3 rounded-panel-nested bg-[#B7791F]/10 border border-[#B7791F]/25 text-[#B7791F] dark:text-[#F6E05E] text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" aria-hidden="true" />
            <span>{submitWarning}</span>
          </div>
        )}

        {success && (
          <div className="p-3 rounded-panel-nested bg-[#0E8F9C]/10 border border-[#0E8F9C]/25 text-[#0E8F9C] dark:text-[#81E6D9] text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" aria-hidden="true" />
            <span>Official asset registered successfully. Closing dialog...</span>
          </div>
        )}

        {/* STEP 1: PREFILL FIRST */}
        {step === "PREFILL" && (
          <div className="space-y-4 rounded-panel-nested bg-surface-2 border border-hairline p-4">
            <div className="flex items-center justify-between pb-2 border-b border-hairline">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-ink">
                <Sparkles className="w-3.5 h-3.5 text-lens" aria-hidden="true" />
                <span>Store Prefill & Auto-Discovery</span>
              </div>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => setPrefillMode("URL")}
                  className={cn(
                    "px-2.5 py-1 rounded-pill text-[10px] font-semibold transition-colors",
                    prefillMode === "URL"
                      ? "bg-ink text-surface dark:bg-surface dark:text-ink"
                      : "text-ink-muted hover:text-ink"
                  )}
                >
                  Store Link
                </button>
                <button
                  type="button"
                  onClick={() => setPrefillMode("ID")}
                  className={cn(
                    "px-2.5 py-1 rounded-pill text-[10px] font-semibold transition-colors",
                    prefillMode === "ID"
                      ? "bg-ink text-surface dark:bg-surface dark:text-ink"
                      : "text-ink-muted hover:text-ink"
                  )}
                >
                  Platform & ID
                </button>
              </div>
            </div>

            {prefillMode === "URL" ? (
              <div className="space-y-1.5">
                <label htmlFor="prefill-url" className="text-xs font-medium text-ink">
                  Paste Store or Profile Link
                </label>
                <input
                  id="prefill-url"
                  type="url"
                  value={prefillUrl}
                  onChange={(e) => setPrefillUrl(e.target.value)}
                  placeholder="https://apps.apple.com/in/app/kaveri-bank/id1234567890"
                  className="w-full px-3 py-2 rounded-xl bg-surface border border-hairline font-mono text-xs text-ink placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-lens"
                />
                <p className="text-[10px] text-ink-muted">
                  Allowed patterns: <code className="font-mono">apps.apple.com/&lt;cc&gt;/app/&lt;slug&gt;/id&lt;digits&gt;</code> or <code className="font-mono">bsky.app/profile/&lt;handle&gt;</code>
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label htmlFor="prefill-platform" className="text-xs font-medium text-ink">
                    Platform
                  </label>
                  <select
                    id="prefill-platform"
                    value={prefillPlatform}
                    onChange={(e) => setPrefillPlatform(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-surface border border-hairline text-xs text-ink focus:outline-none focus:ring-2 focus:ring-lens"
                  >
                    <option value="apple_app_store">Apple App Store</option>
                    <option value="bluesky">Bluesky</option>
                  </select>
                </div>
                <div className="space-y-1">
                  <label htmlFor="prefill-identifier" className="text-xs font-medium text-ink">
                    Identifier
                  </label>
                  <input
                    id="prefill-identifier"
                    type="text"
                    value={prefillIdentifier}
                    onChange={(e) => setPrefillIdentifier(e.target.value)}
                    placeholder="e.g. 1234567890 or handle"
                    className="w-full px-3 py-2 rounded-xl bg-surface border border-hairline font-mono text-xs text-ink placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-lens"
                  />
                </div>
              </div>
            )}

            {/* Error & Empty Notices */}
            {prefillError && (
              <div className="p-3 rounded-lg bg-[#A4123F]/10 border border-[#A4123F]/25 text-[#A4123F] dark:text-[#FEB2B2] text-xs">
                {prefillError}
              </div>
            )}

            {prefillEmptyNotice && (
              <div className="p-3 rounded-lg bg-surface border border-hairline text-xs space-y-2">
                <p className="text-ink-muted">{prefillEmptyNotice}</p>
                <button
                  type="button"
                  onClick={() => setStep("FORM")}
                  className="px-3 py-1 rounded-pill bg-ink text-surface dark:bg-surface dark:text-ink text-xs font-semibold"
                >
                  Continue with Manual Entry →
                </button>
              </div>
            )}

            <div className="flex items-center justify-between pt-1">
              <button
                type="button"
                onClick={() => setStep("FORM")}
                className="text-xs text-ink-muted hover:text-ink underline"
              >
                Skip Prefill (Manual Entry)
              </button>

              <button
                type="button"
                disabled={prefillMutation.isPending || (prefillMode === "URL" ? !prefillUrl : !prefillIdentifier)}
                onClick={() => prefillMutation.mutate()}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-pill bg-ink text-surface dark:bg-surface dark:text-ink text-xs font-semibold hover:opacity-90 disabled:opacity-50 transition-opacity focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lens"
              >
                {prefillMutation.isPending ? (
                  <span className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Search className="w-3.5 h-3.5" aria-hidden="true" />
                )}
                <span>Fetch Metadata</span>
              </button>
            </div>
          </div>
        )}

        {/* STEP 2: EDITABLE REGISTRATION FORM */}
        {step === "FORM" && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              createMutation.mutate();
            }}
            className="space-y-4"
          >
            {prefillNotice && (
              <div className="flex items-center justify-between p-3 rounded-panel-nested bg-surface-2 border border-hairline text-xs">
                <div className="flex items-center gap-2">
                  <SourceBadge status={prefillNotice.source_mode} />
                  <span className="text-ink-muted">
                    Draft retrieved from <strong className="text-ink">{prefillNotice.source_id}</strong> at{" "}
                    {new Date(prefillNotice.retrieved_at).toLocaleTimeString()}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setStep("PREFILL")}
                  className="text-lens font-semibold hover:underline"
                >
                  Change Link
                </button>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {/* Asset Type */}
              <div className="space-y-1">
                <label htmlFor="asset-type-select" className="text-xs font-semibold text-ink">
                  Asset Type *
                </label>
                <select
                  id="asset-type-select"
                  value={assetType}
                  onChange={(e) => setAssetType(e.target.value as Schema["AssetType"])}
                  className="w-full px-3 py-2 rounded-xl bg-surface-2 border border-hairline text-xs text-ink focus:outline-none focus:ring-2 focus:ring-lens"
                >
                  <option value="IOS_APP">iOS Application</option>
                  <option value="ANDROID_APP">Android Application</option>
                  <option value="SOCIAL_ACCOUNT">Social Media Account</option>
                </select>
              </div>

              {/* Platform */}
              <div className="space-y-1">
                <label htmlFor="platform-select" className="text-xs font-semibold text-ink">
                  Platform *
                </label>
                <select
                  id="platform-select"
                  value={platform}
                  onChange={(e) => setPlatform(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-surface-2 border border-hairline text-xs text-ink focus:outline-none focus:ring-2 focus:ring-lens"
                >
                  <option value="apple_app_store">Apple App Store</option>
                  <option value="bluesky">Bluesky</option>
                  <option value="google_play">Google Play</option>
                  <option value="instagram">Instagram</option>
                  <option value="x">X (Twitter)</option>
                  <option value="facebook">Facebook</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {/* Display Name */}
              <div className="space-y-1">
                <label htmlFor="asset-display-name" className="text-xs font-semibold text-ink">
                  Display Name *
                </label>
                <input
                  id="asset-display-name"
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  required
                  placeholder="e.g. Kaveri Bank"
                  className="w-full px-3 py-2 rounded-xl bg-surface-2 border border-hairline text-xs text-ink placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-lens"
                />
              </div>

              {/* Stable Identifier */}
              <div className="space-y-1">
                <label htmlFor="asset-stable-id" className="text-xs font-semibold text-ink flex items-center justify-between">
                  <span>Stable Identifier *</span>
                  <span className="text-[10px] text-ink-muted font-mono">numeric for Apple, did for Bluesky</span>
                </label>
                <input
                  id="asset-stable-id"
                  type="text"
                  value={stableIdentifier}
                  onChange={(e) => setStableIdentifier(e.target.value)}
                  required
                  placeholder="e.g. 1234567890"
                  className="w-full px-3 py-2 rounded-xl bg-surface-2 border border-hairline font-mono text-xs text-ink placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-lens"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {/* Publisher Name */}
              <div className="space-y-1">
                <label htmlFor="asset-publisher-name" className="text-xs font-semibold text-ink">
                  Publisher / Organization Name
                </label>
                <input
                  id="asset-publisher-name"
                  type="text"
                  value={publisherName}
                  onChange={(e) => setPublisherName(e.target.value)}
                  placeholder="e.g. Kaveri Bank Ltd"
                  className="w-full px-3 py-2 rounded-xl bg-surface-2 border border-hairline text-xs text-ink placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-lens"
                />
              </div>

              {/* Developer ID */}
              <div className="space-y-1">
                <label htmlFor="asset-developer-id" className="text-xs font-semibold text-ink">
                  Developer / Account ID
                </label>
                <input
                  id="asset-developer-id"
                  type="text"
                  value={developerId}
                  onChange={(e) => setDeveloperId(e.target.value)}
                  placeholder="e.g. 9000000001"
                  className="w-full px-3 py-2 rounded-xl bg-surface-2 border border-hairline font-mono text-xs text-ink placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-lens"
                />
              </div>
            </div>

            {/* Secondary Identifiers (Bundle ID) */}
            {assetType === "IOS_APP" && (
              <div className="space-y-1">
                <label htmlFor="asset-bundle-id" className="text-xs font-semibold text-ink">
                  Bundle Identifier (R1_EXACT_ID match)
                </label>
                <input
                  id="asset-bundle-id"
                  type="text"
                  value={bundleId}
                  onChange={(e) => setBundleId(e.target.value)}
                  placeholder="com.kaveribank.mobile"
                  className="w-full px-3 py-2 rounded-xl bg-surface-2 border border-hairline font-mono text-xs text-ink placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-lens"
                />
              </div>
            )}

            {/* Social Handle */}
            {assetType === "SOCIAL_ACCOUNT" && (
              <div className="space-y-1">
                <label htmlFor="asset-handle" className="text-xs font-semibold text-ink">
                  Handle / Domain Verified Slug
                </label>
                <input
                  id="asset-handle"
                  type="text"
                  value={handle}
                  onChange={(e) => setHandle(e.target.value)}
                  placeholder="kaveribank.example"
                  className="w-full px-3 py-2 rounded-xl bg-surface-2 border border-hairline font-mono text-xs text-ink placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-lens"
                />
              </div>
            )}

            {/* Canonical URL & Icon URL */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label htmlFor="asset-canonical-url" className="text-xs font-semibold text-ink">
                  Canonical URL *
                </label>
                <input
                  id="asset-canonical-url"
                  type="url"
                  value={canonicalUrl}
                  onChange={(e) => setCanonicalUrl(e.target.value)}
                  required
                  placeholder="https://apps.apple.com/..."
                  className="w-full px-3 py-2 rounded-xl bg-surface-2 border border-hairline font-mono text-xs text-ink placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-lens"
                />
              </div>
              <div className="space-y-1">
                <label htmlFor="asset-icon-url" className="text-xs font-semibold text-ink">
                  Icon / Avatar URL
                </label>
                <input
                  id="asset-icon-url"
                  type="url"
                  value={iconUrl}
                  onChange={(e) => setIconUrl(e.target.value)}
                  placeholder="https://..."
                  className="w-full px-3 py-2 rounded-xl bg-surface-2 border border-hairline font-mono text-xs text-ink placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-lens"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {/* Relationship */}
              <div className="space-y-1">
                <label htmlFor="asset-relationship" className="text-xs font-semibold text-ink">
                  Relationship
                </label>
                <select
                  id="asset-relationship"
                  value={relationship}
                  onChange={(e) => setRelationship(e.target.value as Schema["Relationship"])}
                  className="w-full px-3 py-2 rounded-xl bg-surface-2 border border-hairline text-xs text-ink focus:outline-none focus:ring-2 focus:ring-lens"
                >
                  <option value="OFFICIAL">Official Brand Asset</option>
                  <option value="AUTHORIZED_PARTNER">Authorized Partner</option>
                </select>
              </div>

              {/* Verification Method */}
              <div className="space-y-1">
                <label htmlFor="asset-verification-method" className="text-xs font-semibold text-ink">
                  Verification Method
                </label>
                <select
                  id="asset-verification-method"
                  value={verificationMethod}
                  onChange={(e) =>
                    setVerificationMethod(e.target.value as Schema["VerificationMethod"])
                  }
                  className="w-full px-3 py-2 rounded-xl bg-surface-2 border border-hairline text-xs text-ink focus:outline-none focus:ring-2 focus:ring-lens"
                >
                  <option value="STORE_LOOKUP">Store Lookup</option>
                  <option value="DOMAIN_VERIFIED_HANDLE">Domain Verified Handle</option>
                  <option value="OWNER_PROVIDED">Owner Provided</option>
                </select>
              </div>
            </div>

            {/* Checkbox Controls */}
            <div className="p-3 rounded-panel-nested bg-surface-2 border border-hairline space-y-2">
              <label className="flex items-start gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isVerified}
                  onChange={(e) => setIsVerified(e.target.checked)}
                  className="mt-0.5 rounded text-lens focus:ring-lens"
                />
                <div className="text-xs">
                  <span className="font-semibold text-ink block">Analyst Verified Identity</span>
                  <span className="text-[11px] text-ink-muted">
                    Non-negotiable rule: Never auto-set is_verified from a name match. Mark true only with verified developer or domain evidence.
                  </span>
                </div>
              </label>

              <label className="flex items-start gap-2.5 cursor-pointer pt-2 border-t border-hairline">
                <input
                  type="checkbox"
                  checked={trustPublisher}
                  onChange={(e) => setTrustPublisher(e.target.checked)}
                  className="mt-0.5 rounded text-lens focus:ring-lens"
                />
                <div className="text-xs">
                  <span className="font-semibold text-ink block">Trust Developer ID (Rule R2)</span>
                  <span className="text-[11px] text-ink-muted">
                    Automatically clears secondary apps published under this developer ID with rule R2_PUBLISHER_ID.
                  </span>
                </div>
              </label>
            </div>

            {/* Notes */}
            <div className="space-y-1">
              <label htmlFor="asset-notes" className="text-xs font-semibold text-ink">
                Internal Analyst Notes
              </label>
              <textarea
                id="asset-notes"
                rows={2}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Optional registry notes or authorized context."
                className="w-full px-3 py-2 rounded-xl bg-surface-2 border border-hairline text-xs text-ink placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-lens"
              />
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-hairline">
              <button
                type="button"
                onClick={() => setStep("PREFILL")}
                className="px-4 py-2 rounded-pill text-xs font-semibold text-ink-muted hover:text-ink transition-colors"
              >
                Back
              </button>
              <button
                type="submit"
                disabled={createMutation.isPending || !stableIdentifier || !displayName}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-pill bg-ink text-surface dark:bg-surface dark:text-ink text-xs font-semibold hover:opacity-90 disabled:opacity-50 transition-opacity focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lens"
              >
                {createMutation.isPending ? (
                  <span className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Plus className="w-3.5 h-3.5" aria-hidden="true" />
                )}
                <span>Confirm & Register Asset</span>
              </button>
            </div>
          </form>
        )}
      </div>
    </Dialog>
  );
}
