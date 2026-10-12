import React, { useState, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import { ApiError } from "@/api/errors";
import type { Schema } from "@/api/client";
import { Building2, Save, CheckCircle2, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface BrandFormProps {
  brand: Schema["Brand"];
}

export function BrandForm({ brand }: BrandFormProps) {
  const queryClient = useQueryClient();

  const [name, setName] = useState(brand.name);
  const [description, setDescription] = useState(brand.description || "");
  const [domainsInput, setDomainsInput] = useState(brand.official_domains.join(", "));
  const [keywordsInput, setKeywordsInput] = useState(brand.keywords.join(", "));
  const [distinctiveTokensInput, setDistinctiveTokensInput] = useState(
    brand.distinctive_tokens.join(", ")
  );
  const [category, setCategory] = useState(brand.industry_category || "Finance");
  const [demoBrand, setDemoBrand] = useState(brand.demo_brand);

  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Sync if brand changes
  useEffect(() => {
    setName(brand.name);
    setDescription(brand.description || "");
    setDomainsInput(brand.official_domains.join(", "));
    setKeywordsInput(brand.keywords.join(", "));
    setDistinctiveTokensInput(brand.distinctive_tokens.join(", "));
    setCategory(brand.industry_category || "Finance");
    setDemoBrand(brand.demo_brand);
    setFieldErrors({});
    setGeneralError(null);
  }, [brand]);

  const updateMutation = useMutation({
    mutationFn: async (data: Schema["BrandUpdate"] & { demo_brand?: boolean }) => {
      return apiClient.patchBrand(brand.id, data);
    },
    onSuccess: () => {
      setFieldErrors({});
      setGeneralError(null);
      setSuccessMessage("Brand profile configuration saved successfully.");
      queryClient.invalidateQueries({ queryKey: ["brands"] });
      queryClient.invalidateQueries({ queryKey: ["brand-summary", brand.id] });
      setTimeout(() => setSuccessMessage(null), 4000);
    },
    onError: (err: unknown) => {
      setSuccessMessage(null);
      if (err instanceof ApiError && err.status === 422 && err.details) {
        const errors: Record<string, string> = {};
        for (const detail of err.details) {
          if (detail.field) {
            errors[detail.field] = detail.issue;
          }
        }
        setFieldErrors(errors);
        setGeneralError(err.message || "Please resolve field validation issues.");
      } else if (err instanceof ApiError) {
        setGeneralError(`Error (${err.code}): ${err.message}`);
      } else {
        setGeneralError("An unexpected error occurred while updating the brand profile.");
      }
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setGeneralError(null);
    setSuccessMessage(null);

    // Client validation per section 11.2
    const errors: Record<string, string> = {};
    if (name.trim().length < 2 || name.trim().length > 60) {
      errors.name = "Name must be between 2 and 60 characters.";
    }

    const officialDomains = domainsInput
      .split(/[\n,]/)
      .map((d) => d.trim())
      .filter(Boolean);

    for (const d of officialDomains) {
      if (/^https?:\/\//i.test(d) || d.includes("/") || /\s/.test(d)) {
        errors.official_domains = `Domain '${d}' must be a hostname only (no scheme http:// or path /).`;
        break;
      }
    }

    const keywords = keywordsInput
      .split(/[\n,]/)
      .map((k) => k.trim())
      .filter(Boolean);

    if (keywords.length > 12) {
      errors.keywords = "Maximum 12 keywords allowed per brand.";
    }

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      setGeneralError("Validation requirements not met. Please review inline errors.");
      return;
    }

    const distinctiveTokens = distinctiveTokensInput
      .split(/[\n,]/)
      .map((t) => t.trim().toLowerCase())
      .filter(Boolean);

    updateMutation.mutate({
      name: name.trim(),
      description: description.trim(),
      official_domains: officialDomains,
      keywords,
      distinctive_tokens: distinctiveTokens,
      industry_category: category,
      demo_brand: demoBrand,
    } as Schema["BrandUpdate"]);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-panel-nested border border-hairline bg-surface p-6 space-y-5 shadow-sm"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-hairline">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-surface-2 border border-hairline flex items-center justify-center text-lens shrink-0">
            <Building2 className="w-4 h-4" aria-hidden="true" />
          </div>
          <div>
            <h2 className="font-display font-semibold text-base text-ink tracking-tight">
              Brand Profile Details
            </h2>
            <p className="text-xs text-ink-muted">
              Defines legitimate identity, distinctive tokens, and authorized hostnames.
            </p>
          </div>
        </div>

        <button
          type="submit"
          disabled={updateMutation.isPending}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-pill bg-ink text-surface dark:bg-surface dark:text-ink text-xs font-semibold hover:opacity-90 transition-opacity focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lens self-start sm:self-auto disabled:opacity-50"
        >
          {updateMutation.isPending ? (
            <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
          ) : (
            <Save className="w-3.5 h-3.5" aria-hidden="true" />
          )}
          <span>Save Configuration</span>
        </button>
      </div>

      {/* Global Alerts */}
      {generalError && (
        <div className="p-3.5 rounded-panel-nested bg-[#A4123F]/10 border border-[#A4123F]/25 text-[#A4123F] dark:text-[#FEB2B2] text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
          <span>{generalError}</span>
        </div>
      )}

      {successMessage && (
        <div className="p-3.5 rounded-panel-nested bg-[#0E8F9C]/10 border border-[#0E8F9C]/25 text-[#0E8F9C] dark:text-[#81E6D9] text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" aria-hidden="true" />
          <span>{successMessage}</span>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Name */}
        <div className="space-y-1.5">
          <label htmlFor="brand-name" className="text-xs font-semibold text-ink flex items-center justify-between">
            <span>Brand Name *</span>
            <span className="text-[10px] text-ink-muted">2–60 characters</span>
          </label>
          <input
            id="brand-name"
            type="text"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              if (fieldErrors.name) setFieldErrors((prev) => ({ ...prev, name: "" }));
            }}
            className={cn(
              "w-full px-3.5 py-2 rounded-xl bg-surface-2 border text-xs text-ink placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-lens",
              fieldErrors.name ? "border-[#A4123F] bg-[#A4123F]/5" : "border-hairline"
            )}
            placeholder="e.g. Kaveri Bank"
            required
          />
          {fieldErrors.name && (
            <p className="text-[11px] text-[#A4123F] font-medium">{fieldErrors.name}</p>
          )}
        </div>

        {/* Industry Category */}
        <div className="space-y-1.5">
          <label htmlFor="brand-category" className="text-xs font-semibold text-ink">
            Industry Category
          </label>
          <select
            id="brand-category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="w-full px-3.5 py-2 rounded-xl bg-surface-2 border border-hairline text-xs text-ink focus:outline-none focus:ring-2 focus:ring-lens"
          >
            <option value="Finance">Finance / Banking</option>
            <option value="Retail">Retail / E-commerce</option>
            <option value="Healthcare">Healthcare</option>
            <option value="Technology">Technology / SaaS</option>
            <option value="Telecom">Telecommunications</option>
            <option value="Travel">Travel & Hospitality</option>
          </select>
        </div>
      </div>

      {/* Description */}
      <div className="space-y-1.5">
        <label htmlFor="brand-description" className="text-xs font-semibold text-ink">
          Descriptor Summary
        </label>
        <textarea
          id="brand-description"
          rows={2}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="w-full px-3.5 py-2 rounded-xl bg-surface-2 border border-hairline text-xs text-ink placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-lens"
          placeholder="Brief summary of brand mission used for TF-IDF bio similarity scoring."
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Official Domains */}
        <div className="space-y-1.5">
          <label htmlFor="brand-domains" className="text-xs font-semibold text-ink flex items-center justify-between">
            <span>Official Domains *</span>
            <span className="text-[10px] text-ink-muted font-mono">hostnames only (comma separated)</span>
          </label>
          <input
            id="brand-domains"
            type="text"
            value={domainsInput}
            onChange={(e) => {
              setDomainsInput(e.target.value);
              if (fieldErrors.official_domains) setFieldErrors((prev) => ({ ...prev, official_domains: "" }));
            }}
            className={cn(
              "w-full px-3.5 py-2 rounded-xl bg-surface-2 border font-mono text-xs text-ink placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-lens",
              fieldErrors.official_domains ? "border-[#A4123F] bg-[#A4123F]/5" : "border-hairline"
            )}
            placeholder="kaveribank.example, kaveri-secure.com"
          />
          {fieldErrors.official_domains && (
            <p className="text-[11px] text-[#A4123F] font-medium">{fieldErrors.official_domains}</p>
          )}
          <p className="text-[10px] text-ink-muted">
            Used by link_domain_mismatch signal. Never include http:// or path suffixes.
          </p>
        </div>

        {/* Distinctive Tokens */}
        <div className="space-y-1.5">
          <label htmlFor="brand-distinctive" className="text-xs font-semibold text-ink flex items-center justify-between">
            <span>Distinctive Name Tokens</span>
            <span className="text-[10px] text-ink-muted">weight 1.0 (vs generic 0.2)</span>
          </label>
          <input
            id="brand-distinctive"
            type="text"
            value={distinctiveTokensInput}
            onChange={(e) => setDistinctiveTokensInput(e.target.value)}
            className="w-full px-3.5 py-2 rounded-xl bg-surface-2 border border-hairline font-mono text-xs text-ink placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-lens"
            placeholder="e.g. kaveri"
          />
          <p className="text-[10px] text-ink-muted">
            Tokens weighted at 1.0 during normalized name scoring (e.g. 'kaveri' vs generic 'bank').
          </p>
        </div>
      </div>

      {/* Keywords */}
      <div className="space-y-1.5">
        <label htmlFor="brand-keywords" className="text-xs font-semibold text-ink flex items-center justify-between">
          <span>Search & Query Planner Keywords</span>
          <span className="text-[10px] text-ink-muted">maximum 12 keywords</span>
        </label>
        <input
          id="brand-keywords"
          type="text"
          value={keywordsInput}
          onChange={(e) => {
            setKeywordsInput(e.target.value);
            if (fieldErrors.keywords) setFieldErrors((prev) => ({ ...prev, keywords: "" }));
          }}
          className={cn(
            "w-full px-3.5 py-2 rounded-xl bg-surface-2 border text-xs text-ink placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-lens",
            fieldErrors.keywords ? "border-[#A4123F] bg-[#A4123F]/5" : "border-hairline"
          )}
          placeholder="Kaveri Bank, KaveriBank, Kaveri Mobile, Kaveri Pay"
        />
        {fieldErrors.keywords && (
          <p className="text-[11px] text-[#A4123F] font-medium">{fieldErrors.keywords}</p>
        )}
      </div>

      {/* Demo Brand Toggle */}
      <div className="pt-2 border-t border-hairline flex items-center justify-between">
        <div>
          <span className="text-xs font-semibold text-ink block">Demo Fixture Brand</span>
          <span className="text-[11px] text-ink-muted">
            When enabled, all alerts across the app carry the persistent demo notice.
          </span>
        </div>
        <label className="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={demoBrand}
            onChange={(e) => setDemoBrand(e.target.checked)}
            className="sr-only peer"
          />
          <div className="w-11 h-6 bg-surface-2 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-lens rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-lens border border-hairline" />
        </label>
      </div>
    </form>
  );
}
