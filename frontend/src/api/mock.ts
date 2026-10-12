import { ApiError } from "./errors";
import type { ApiClient, Schema } from "./client";
import {
  BRAND_ID,
  SCAN_ID,
  MOCK_BRAND,
  MOCK_ASSETS,
  MOCK_SOURCES_STATUS,
  MOCK_FINDINGS,
  MOCK_CLEARED,
  MOCK_SCAN_DETAIL,
  MOCK_SCANS_LIST,
  MOCK_AUDIT,
  MOCK_DATASETS,
  getMockComparison,
} from "./mock-data/fixtures";
import {
  MOCK_EVAL_CASES,
  computeEvaluationMetrics,
} from "./mock-data/evaluation";

interface ActiveScanRecord {
  id: string;
  brand_id: string;
  mode: Schema["ScanMode"];
  options: Schema["ScanCreate"];
  createdAt: number;
}

// In-memory state that persists during application runtime
class InMemoryDatabase {
  brands: Schema["Brand"][] = [{ ...MOCK_BRAND }];
  assets: Schema["OfficialAsset"][] = MOCK_ASSETS.map((a) => ({ ...a }));
  findings: Schema["FindingDetail"][] = MOCK_FINDINGS.map((f) => ({ ...f }));
  cleared: Schema["ClearedItem"][] = MOCK_CLEARED.map((c) => ({ ...c }));
  scans: Schema["ScanDetail"][] = [{ ...MOCK_SCAN_DETAIL }];
  scansList: Schema["ScanSummaryItem"][] = [{ ...MOCK_SCANS_LIST[0] }];
  audit: Schema["AuditEvent"][] = MOCK_AUDIT.map((a) => ({ ...a }));
  activeScans: Map<string, ActiveScanRecord> = new Map();
}

const db = new InMemoryDatabase();

export const mockApiClient: ApiClient = {
  // 11.1 Health and meta
  async getHealth() {
    return {
      status: "ok",
      service: "threatlens-api",
      version: "3.0.0",
      contract_version: "3.0.0",
    };
  },

  async getReady() {
    return {
      ready: true,
      checks: {
        database: "ok",
        config: "ok",
      },
    };
  },

  async getMeta() {
    return {
      scoring_version: "3.0.0",
      relevance_threshold: 0.6,
      review_threshold: 25,
      severity_bands: {
        LOW: [0, 24],
        MEDIUM: [25, 49],
        HIGH: [50, 74],
        CRITICAL: [75, 100],
      },
      enums: {
        ScanMode: ["LIVE", "DEMO"],
        SourceMode: ["LIVE", "CACHED", "SIMULATED"],
        SourceStatus: ["CONNECTED", "PARTIAL", "NOT_CONNECTED", "RATE_LIMITED", "ERROR"],
        Severity: ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
      },
      supported_platforms: ["apple_app_store", "bluesky", "google_play", "instagram", "x", "facebook"],
      supported_asset_types: ["IOS_APP", "ANDROID_APP", "SOCIAL_ACCOUNT"],
    };
  },

  async getSourcesStatus(_refresh = false) {
    return MOCK_SOURCES_STATUS;
  },

  // 11.2 Brands
  async getBrands(params) {
    const offset = params?.offset || 0;
    const limit = params?.limit || 20;
    return {
      items: db.brands.slice(offset, offset + limit),
      total: db.brands.length,
      limit,
      offset,
    };
  },

  async createBrand(data) {
    const brand: Schema["Brand"] = {
      id: "brand-" + Math.random().toString(36).substring(2, 9),
      name: data.name,
      description: data.description,
      official_domains: data.official_domains,
      keywords: data.keywords,
      distinctive_tokens: data.distinctive_tokens,
      industry_category: data.industry_category,
      demo_brand: data.demo_brand ?? true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    db.brands.push(brand);
    return brand;
  },

  async getBrand(brandId) {
    const found = db.brands.find((b) => b.id === brandId);
    if (!found) {
      throw new ApiError(404, {
        code: "NOT_FOUND",
        message: `Brand ${brandId} not found.`,
        request_id: "req-mock-brand-404",
      });
    }
    return found;
  },

  async patchBrand(brandId, data) {
    const index = db.brands.findIndex((b) => b.id === brandId);
    if (index === -1) {
      throw new ApiError(404, {
        code: "NOT_FOUND",
        message: `Brand ${brandId} not found.`,
        request_id: "req-mock-brand-404",
      });
    }

    // Validation per section 11.2
    const validationDetails: Array<{ field?: string; issue: string }> = [];

    if (data.name !== undefined) {
      if (data.name.trim().length < 2 || data.name.trim().length > 60) {
        validationDetails.push({
          field: "name",
          issue: "Brand name must be between 2 and 60 characters.",
        });
      }
    }

    if (data.official_domains !== undefined) {
      for (const domain of data.official_domains) {
        if (/^https?:\/\//i.test(domain) || domain.includes("/") || /\s/.test(domain)) {
          validationDetails.push({
            field: "official_domains",
            issue: `Invalid domain '${domain}'. Must be a hostname only (no scheme http:// or path /).`,
          });
        }
      }
    }

    if (data.keywords !== undefined && data.keywords.length > 12) {
      validationDetails.push({
        field: "keywords",
        issue: "Keywords list cannot exceed 12 items.",
      });
    }

    if (validationDetails.length > 0) {
      throw new ApiError(422, {
        code: "VALIDATION_ERROR",
        message: "Invalid fields in brand update request.",
        request_id: "req-mock-val-" + Math.random().toString(36).substring(2, 7),
        details: validationDetails,
      });
    }

    db.brands[index] = {
      ...db.brands[index],
      ...data,
      updated_at: new Date().toISOString(),
    };
    return db.brands[index];
  },

  async getBrandSummary(brandId) {
    const brand = await this.getBrand(brandId);

    // Compute live status counts from memory findings
    const findingsByStatus: Record<Schema["FindingStatus"], number> = {
      NEW: 0,
      IN_REVIEW: 0,
      CONFIRMED_SUSPICIOUS: 0,
      DISMISSED_FALSE_POSITIVE: 0,
      INCONCLUSIVE: 0,
    };
    for (const f of db.findings) {
      if (findingsByStatus[f.status] !== undefined) {
        findingsByStatus[f.status]++;
      }
    }

    const reviewed =
      findingsByStatus.CONFIRMED_SUSPICIOUS +
      findingsByStatus.DISMISSED_FALSE_POSITIVE +
      findingsByStatus.INCONCLUSIVE;

    return {
      brand_id: brand.id,
      official_asset_count: db.assets.filter((a) => a.brand_id === brand.id).length,
      last_scan: {
        id: SCAN_ID,
        mode: "DEMO",
        status: "COMPLETED",
        completed_at: "2026-10-12T05:31:00Z",
      },
      funnel: MOCK_SCAN_DETAIL.funnel,
      findings_by_severity: MOCK_SCAN_DETAIL.findings_by_severity,
      findings_by_status: findingsByStatus,
      findings_by_platform: {
        apple_app_store: 1,
        bluesky: 4,
        google_play: 1,
        instagram: 2,
        x: 2,
        facebook: 2,
      },
      cleared_by_decision: {
        OFFICIAL_EXACT_MATCH: 3,
        OFFICIAL_PUBLISHER_MATCH: 1,
        AUTHORIZED_PARTNER_MATCH: 1,
        BENIGN_LOOKALIKE: 14,
        BELOW_THRESHOLD: 0,
        CANDIDATE_FOR_REVIEW: 0,
      },
      review_progress: {
        reviewed,
        total: db.findings.length,
      },
      source_coverage: [
        {
          source_id: "apple_itunes",
          status: "CONNECTED",
          source_mode: "LIVE",
          retrieved_at: "2026-10-12T05:30:35Z",
        },
        {
          source_id: "bluesky_public",
          status: "RATE_LIMITED",
          source_mode: "LIVE",
          retrieved_at: "2026-10-12T05:30:40Z",
        },
        {
          source_id: "google_play_snapshot",
          status: "NOT_CONNECTED",
          source_mode: null,
          retrieved_at: null,
        },
      ],
      latest_evaluation: {
        id: "eval-30000000-0000-0000-0000-000000000001",
        split: "HELDOUT",
        precision: 0.94,
        recall: 0.88,
        created_at: "2026-10-12T05:30:00Z",
      },
    };
  },

  // 11.3 Official assets
  async prefillAsset(_brandId, data) {
    const rawUrl = data.url || "";
    const platform = data.platform || "";
    const identifier = data.identifier || "";

    // Test blocked URLs
    if (rawUrl) {
      const isApple = /apps\.apple\.com\/[a-z]{2}\/app\/[^/]+\/id\d+/i.test(rawUrl) || rawUrl.includes("apps.apple.com");
      const isBluesky = /bsky\.app\/profile\/[^/]+/i.test(rawUrl) || rawUrl.includes("bsky.app");

      if (!isApple && !isBluesky) {
        throw new ApiError(422, {
          code: "BLOCKED_URL",
          message: "Disallowed prefill URL pattern.",
          request_id: "req-prefill-blocked-422",
          details: [
            {
              field: "url",
              issue: "BLOCKED_URL: Host is not allowlisted. Only apps.apple.com and bsky.app profiles are permitted.",
            },
          ],
        });
      }

      // Check if testing simulated provider failure or draft: null
      if (rawUrl.includes("fail") || rawUrl.includes("notfound") || rawUrl.includes("404")) {
        return {
          source_id: isApple ? "apple_itunes" : "bluesky_public",
          source_mode: "LIVE",
          retrieved_at: new Date().toISOString(),
          draft: null,
          source_status: "NOT_CONNECTED",
          error_code: "PROVIDER_UNAVAILABLE",
          message: "Asset could not be found in public catalog. Please enter details manually.",
        };
      }

      if (isBluesky) {
        const handleMatch = rawUrl.match(/profile\/([^/?#]+)/);
        const handle = handleMatch ? handleMatch[1] : "kaveribank.example";
        return {
          source_id: "bluesky_public",
          source_mode: "LIVE",
          retrieved_at: new Date().toISOString(),
          draft: {
            asset_type: "SOCIAL_ACCOUNT",
            platform: "bluesky",
            stable_identifier: `did:plc:${handle.replace(/\./g, "")}`,
            secondary_identifiers: {},
            developer_id: null,
            publisher_name: null,
            display_name: "Kaveri Bank Official",
            description: "Official Bluesky handle for Kaveri Bank.",
            category: "Finance",
            canonical_url: rawUrl,
            icon_url: "https://cdn.bsky.app/avatar_official.png",
            verification_method: "DOMAIN_VERIFIED_HANDLE",
            relationship: "OFFICIAL",
            trust_publisher: false,
          },
        };
      }

      // Default Apple App Store lookup
      const idMatch = rawUrl.match(/id(\d+)/);
      const stableId = idMatch ? idMatch[1] : "1234567890";
      return {
        source_id: "apple_itunes",
        source_mode: "LIVE",
        retrieved_at: new Date().toISOString(),
        draft: {
          asset_type: "IOS_APP",
          platform: "apple_app_store",
          stable_identifier: stableId,
          secondary_identifiers: { bundle_id: "com.kaveribank.mobile" },
          developer_id: "9000000001",
          publisher_name: "Kaveri Bank Ltd",
          display_name: "Kaveri Bank",
          description: "Official mobile banking application for Kaveri Bank customers.",
          category: "Finance",
          canonical_url: rawUrl,
          icon_url: "https://assets.mzstatic.com/kaveribank_icon.png",
          verification_method: "STORE_LOOKUP",
          relationship: "OFFICIAL",
          trust_publisher: true,
        },
      };
    }

    // Platform + identifier lookup
    if (platform === "bluesky") {
      return {
        source_id: "bluesky_public",
        source_mode: "LIVE",
        retrieved_at: new Date().toISOString(),
        draft: {
          asset_type: "SOCIAL_ACCOUNT",
          platform: "bluesky",
          stable_identifier: identifier.startsWith("did:") ? identifier : `did:plc:${identifier.replace(/\./g, "")}`,
          secondary_identifiers: {},
          developer_id: null,
          publisher_name: null,
          display_name: identifier,
          description: `Official Bluesky presence: ${identifier}`,
          category: "Finance",
          canonical_url: `https://bsky.app/profile/${identifier}`,
          icon_url: null,
          verification_method: "DOMAIN_VERIFIED_HANDLE",
          relationship: "OFFICIAL",
          trust_publisher: false,
        },
      };
    }

    // Fallback Apple lookup by identifier
    return {
      source_id: "apple_itunes",
      source_mode: "LIVE",
      retrieved_at: new Date().toISOString(),
      draft: {
        asset_type: "IOS_APP",
        platform: "apple_app_store",
        stable_identifier: identifier || "1234567890",
        secondary_identifiers: { bundle_id: "com.kaveribank.mobile" },
        developer_id: "9000000001",
        publisher_name: "Kaveri Bank Ltd",
        display_name: "Kaveri Bank",
        description: "Official mobile banking application.",
        category: "Finance",
        canonical_url: `https://apps.apple.com/app/id${identifier || "1234567890"}`,
        icon_url: "https://assets.mzstatic.com/kaveribank_icon.png",
        verification_method: "STORE_LOOKUP",
        relationship: "OFFICIAL",
        trust_publisher: true,
      },
    };
  },

  async createAsset(brandId, data) {
    // Check uniqueness constraint: (brand_id, platform, stable_identifier)
    const existing = db.assets.find(
      (a) =>
        a.brand_id === brandId &&
        a.platform === data.platform &&
        a.stable_identifier === data.stable_identifier
    );

    if (existing) {
      throw new ApiError(409, {
        code: "CONFLICT",
        message: `Asset with platform '${data.platform}' and identifier '${data.stable_identifier}' already exists for this brand.`,
        request_id: "req-conflict-" + Math.random().toString(36).substring(2, 7),
        details: [
          {
            field: "stable_identifier",
            issue: "Duplicate official asset identifier on this platform.",
          },
        ],
      });
    }

    // Check publisher warning per Section 11.3:
    // "a warning is returned when an asset's publisher differs from other OFFICIAL assets of the same brand"
    let publisherWarning: string | null = null;
    const officialAssetsWithPublisher = db.assets.filter(
      (a) => a.brand_id === brandId && a.relationship === "OFFICIAL" && a.publisher_name
    );

    if (
      data.relationship === "OFFICIAL" &&
      data.publisher_name &&
      officialAssetsWithPublisher.length > 0
    ) {
      const primaryPublisher = officialAssetsWithPublisher[0].publisher_name;
      if (primaryPublisher && primaryPublisher.toLowerCase() !== data.publisher_name.toLowerCase()) {
        publisherWarning = `Notice: Publisher '${data.publisher_name}' differs from registered official publisher '${primaryPublisher}'. Verify developer credentials.`;
      }
    }

    const asset: Schema["OfficialAsset"] = {
      id: "asset-" + Math.random().toString(36).substring(2, 9),
      brand_id: brandId,
      asset_type: data.asset_type,
      platform: data.platform,
      stable_identifier: data.stable_identifier,
      secondary_identifiers: data.secondary_identifiers,
      developer_id: data.developer_id || null,
      publisher_name: data.publisher_name || null,
      display_name: data.display_name,
      handle: data.handle || null,
      description: data.description || "",
      category: data.category || "Finance",
      canonical_url: data.canonical_url,
      icon_url: data.icon_url || null,
      relationship: data.relationship,
      verification_method: data.verification_method,
      is_verified: data.is_verified ?? false,
      trust_publisher: data.trust_publisher ?? false,
      is_active: true,
      notes: data.notes || "",
      warning: publisherWarning,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    db.assets.push(asset);
    return asset;
  },

  async getAssets(brandId, params) {
    let filtered = db.assets.filter((a) => a.brand_id === brandId);
    if (params?.asset_type) filtered = filtered.filter((a) => a.asset_type === params.asset_type);
    if (params?.relationship) filtered = filtered.filter((a) => a.relationship === params.relationship);
    if (params?.is_verified !== undefined) filtered = filtered.filter((a) => a.is_verified === params.is_verified);
    if (params?.is_active !== undefined) filtered = filtered.filter((a) => a.is_active === params.is_active);

    const offset = params?.offset || 0;
    const limit = params?.limit || 20;
    return {
      items: filtered.slice(offset, offset + limit),
      total: filtered.length,
      limit,
      offset,
    };
  },

  async getAsset(brandId, assetId) {
    const found = db.assets.find((a) => a.brand_id === brandId && a.id === assetId);
    if (!found) {
      throw new ApiError(404, {
        code: "NOT_FOUND",
        message: `Asset ${assetId} not found.`,
        request_id: "req-mock-asset-404",
      });
    }
    return found;
  },

  async patchAsset(brandId, assetId, data) {
    const index = db.assets.findIndex((a) => a.brand_id === brandId && a.id === assetId);
    if (index === -1) {
      throw new ApiError(404, {
        code: "NOT_FOUND",
        message: `Asset ${assetId} not found.`,
        request_id: "req-mock-asset-404",
      });
    }
    db.assets[index] = {
      ...db.assets[index],
      ...data,
      updated_at: new Date().toISOString(),
    };
    return db.assets[index];
  },

  // 11.4 Scans
  async createScan(data) {
    // Contract rule: A LIVE mock scan must be refusable (MODE_NOT_ALLOWED path is exercised with demo_fixtures)
    if (data.mode === "LIVE" && (data.source_ids?.includes("demo_fixtures") || data.source_ids?.includes("recorded_fixtures"))) {
      throw new ApiError(422, {
        code: "MODE_NOT_ALLOWED",
        message: "Source 'demo_fixtures' or 'recorded_fixtures' is not allowed in LIVE scans.",
        request_id: "req-mock-mode-not-allowed",
        details: [{ field: "source_ids", issue: "demo_fixtures requires DEMO mode." }],
      });
    }

    // Contract rule: Only one running scan per brand (409 SCAN_ALREADY_RUNNING)
    const targetBrandId = data.brand_id || BRAND_ID;
    for (const [existingId, active] of db.activeScans.entries()) {
      if (active.brand_id === targetBrandId) {
        const elapsed = (Date.now() - active.createdAt) / 1000;
        if (elapsed < 9) {
          throw new ApiError(409, {
            code: "SCAN_ALREADY_RUNNING",
            message: `A scan is already actively running for brand ${targetBrandId}.`,
            request_id: "req-mock-scan-already-running",
            details: [{ field: "scan_id", issue: existingId }],
          });
        }
      }
    }

    const scanId = "scan-" + Math.random().toString(36).substring(2, 9);
    db.activeScans.set(scanId, {
      id: scanId,
      brand_id: data.brand_id || BRAND_ID,
      mode: data.mode,
      options: data,
      createdAt: Date.now(),
    });

    const summary: Schema["ScanSummaryItem"] = {
      id: scanId,
      brand_id: data.brand_id || BRAND_ID,
      mode: data.mode,
      status: "QUEUED",
      stage: "queued",
      progress_percent: 0,
      findings_count: 0,
      cleared_count: 0,
      created_at: new Date().toISOString(),
      completed_at: null,
    };
    db.scansList.unshift(summary);

    return {
      id: scanId,
      brand_id: data.brand_id || BRAND_ID,
      mode: data.mode,
      status: "QUEUED",
      stage: "queued",
      progress_percent: 0,
      created_at: new Date().toISOString(),
    };
  },

  async getScan(scanId) {
    if (scanId === SCAN_ID || scanId === "scan-demo-001") {
      return MOCK_SCAN_DETAIL;
    }

    const active = db.activeScans.get(scanId);
    if (!active) {
      const existing = db.scans.find((s) => s.id === scanId);
      if (existing) return existing;
      throw new ApiError(404, {
        code: "NOT_FOUND",
        message: `Scan ${scanId} not found.`,
        request_id: "req-mock-scan-404",
      });
    }

    // Advance stages and progress at ~1 s per poll per Section 5.2
    const elapsedSec = (Date.now() - active.createdAt) / 1000;
    let stage: Schema["ScanStage"] = "queued";
    let progress_percent = 0;
    let status: Schema["ScanStatus"] = "QUEUED";

    if (elapsedSec < 1) {
      stage = "queued";
      progress_percent = 0;
      status = "QUEUED";
    } else if (elapsedSec < 2) {
      stage = "resolving_brand";
      progress_percent = 5;
      status = "RUNNING";
    } else if (elapsedSec < 3) {
      stage = "planning_queries";
      progress_percent = 10;
      status = "RUNNING";
    } else if (elapsedSec < 5) {
      stage = "fetching";
      progress_percent = 35;
      status = "RUNNING";
    } else if (elapsedSec < 6) {
      stage = "normalizing";
      progress_percent = 60;
      status = "RUNNING";
    } else if (elapsedSec < 7) {
      stage = "hashing_images";
      progress_percent = 70;
      status = "RUNNING";
    } else if (elapsedSec < 8) {
      stage = "assessing";
      progress_percent = 85;
      status = "RUNNING";
    } else if (elapsedSec < 9) {
      stage = "persisting";
      progress_percent = 98;
      status = "RUNNING";
    } else {
      stage = "completed";
      progress_percent = 100;
      status = "COMPLETED";
    }

    // Update list summary
    const listIndex = db.scansList.findIndex((s) => s.id === scanId);
    if (listIndex !== -1) {
      db.scansList[listIndex].status = status;
      db.scansList[listIndex].stage = stage;
      db.scansList[listIndex].progress_percent = progress_percent;
      if (progress_percent === 100) {
        db.scansList[listIndex].findings_count = 12;
        db.scansList[listIndex].cleared_count = 19;
        db.scansList[listIndex].completed_at = new Date().toISOString();
      }
    }

    return {
      id: scanId,
      brand_id: active.brand_id,
      mode: active.mode,
      status,
      stage,
      progress_percent,
      options: {
        asset_types: active.options.asset_types || ["IOS_APP", "SOCIAL_ACCOUNT"],
        source_ids: active.options.source_ids || ["apple_itunes", "bluesky_public"],
        query_limit_per_source: active.options.query_limit_per_source || 25,
        include_icon_similarity: active.options.include_icon_similarity ?? true,
        force_refresh: active.options.force_refresh ?? false,
        allow_stale_cache: active.options.allow_stale_cache ?? false,
      },
      source_outcomes: MOCK_SCAN_DETAIL.source_outcomes,
      funnel: MOCK_SCAN_DETAIL.funnel,
      findings_by_severity: MOCK_SCAN_DETAIL.findings_by_severity,
      events: MOCK_SCAN_DETAIL.events,
      error_message: null,
      created_at: new Date(active.createdAt).toISOString(),
      started_at: new Date(active.createdAt + 1000).toISOString(),
      completed_at: progress_percent === 100 ? new Date().toISOString() : null,
    };
  },

  async getScans(params) {
    const offset = params?.offset || 0;
    const limit = params?.limit || 20;
    return {
      items: db.scansList.slice(offset, offset + limit),
      total: db.scansList.length,
      limit,
      offset,
    };
  },

  async getScanFindings(_scanId, params) {
    const offset = params?.offset || 0;
    const limit = params?.limit || 20;
    const items = db.findings.map((f) => ({
      id: f.id,
      brand_id: f.brand_id,
      scan_id: f.scan_id,
      candidate: f.candidate,
      risk_score: f.risk_score,
      severity: f.severity,
      evidence_coverage: f.evidence_coverage,
      technique: f.technique,
      top_signals: f.top_signals,
      status: f.status,
      source_mode: f.source_mode,
      observed_at: f.observed_at,
      changed_since_decision: f.changed_since_decision,
    }));
    return {
      items: items.slice(offset, offset + limit),
      total: items.length,
      limit,
      offset,
    };
  },

  async getScanCleared(_scanId, params) {
    const offset = params?.offset || 0;
    const limit = params?.limit || 20;
    return {
      items: db.cleared.slice(offset, offset + limit),
      total: db.cleared.length,
      limit,
      offset,
    };
  },

  // 11.5 Findings and comparison
  async getFindings(params) {
    let filtered = [...db.findings];

    if (params?.brand_id) filtered = filtered.filter((f) => f.brand_id === params.brand_id);
    if (params?.scan_id) {
      filtered = filtered.filter(
        (f) => f.scan_id === params.scan_id || params.scan_id === SCAN_ID || params.scan_id?.startsWith("scan-")
      );
    }
    if (!params?.include_dismissed) {
      filtered = filtered.filter((f) => f.status !== "DISMISSED_FALSE_POSITIVE");
    }
    if (params?.status) filtered = filtered.filter((f) => f.status === params.status);
    if (params?.severity) filtered = filtered.filter((f) => f.severity === params.severity);
    if (params?.platform) filtered = filtered.filter((f) => f.candidate.platform === params.platform);
    if (params?.asset_type) filtered = filtered.filter((f) => f.candidate.asset_type === params.asset_type);
    if (params?.source_mode) filtered = filtered.filter((f) => f.source_mode === params.source_mode);
    if (params?.min_score !== undefined) filtered = filtered.filter((f) => f.risk_score >= params.min_score!);
    if (params?.q) {
      const q = params.q.toLowerCase();
      filtered = filtered.filter(
        (f) =>
          f.candidate.display_name.toLowerCase().includes(q) ||
          (f.candidate.handle && f.candidate.handle.toLowerCase().includes(q)) ||
          (f.candidate.publisher_name && f.candidate.publisher_name.toLowerCase().includes(q))
      );
    }

    if (params?.sort === "score_asc") {
      filtered.sort((a, b) => a.risk_score - b.risk_score);
    } else if (params?.sort === "name_asc") {
      filtered.sort((a, b) => a.candidate.display_name.localeCompare(b.candidate.display_name));
    } else if (params?.sort === "seen_desc") {
      filtered.sort((a, b) => new Date(b.observed_at).getTime() - new Date(a.observed_at).getTime());
    } else {
      filtered.sort((a, b) => b.risk_score - a.risk_score);
    }

    const offset = params?.offset || 0;
    const limit = params?.limit || 20;
    const items = filtered.map((f) => ({
      id: f.id,
      brand_id: f.brand_id,
      scan_id: f.scan_id,
      candidate: f.candidate,
      risk_score: f.risk_score,
      severity: f.severity,
      evidence_coverage: f.evidence_coverage,
      technique: f.technique,
      top_signals: f.top_signals,
      status: f.status,
      source_mode: f.source_mode,
      observed_at: f.observed_at,
      changed_since_decision: f.changed_since_decision,
    }));

    return {
      items: items.slice(offset, offset + limit),
      total: items.length,
      limit,
      offset,
    };
  },

  async getFinding(findingId) {
    const found = db.findings.find((f) => f.id === findingId);
    if (!found) {
      throw new ApiError(404, {
        code: "NOT_FOUND",
        message: `Finding ${findingId} not found.`,
        request_id: "req-mock-finding-404",
      });
    }
    return found;
  },

  async patchFinding(findingId, data) {
    const finding = db.findings.find((f) => f.id === findingId);
    if (!finding) {
      throw new ApiError(404, {
        code: "NOT_FOUND",
        message: `Finding ${findingId} not found.`,
        request_id: "req-mock-finding-404",
      });
    }

    // Contract rule: decision_reason is required for DISMISSED_FALSE_POSITIVE and CONFIRMED_SUSPICIOUS (422 otherwise)
    if (
      (data.status === "DISMISSED_FALSE_POSITIVE" || data.status === "CONFIRMED_SUSPICIOUS") &&
      (!data.decision_reason || data.decision_reason.trim() === "")
    ) {
      throw new ApiError(422, {
        code: "VALIDATION_ERROR",
        message: "decision_reason is required for DISMISSED_FALSE_POSITIVE and CONFIRMED_SUSPICIOUS.",
        request_id: "req-mock-decision-reason-required",
        details: [
          {
            field: "decision_reason",
            issue: "A reasoned explanation is mandatory when confirming or dismissing an alert.",
          },
        ],
      });
    }

    finding.status = data.status;
    finding.decision_history.push({
      at: new Date().toISOString(),
      status: data.status,
      reason: data.decision_reason,
      notes: data.notes,
    });

    // Write audit event
    db.audit.unshift({
      id: "aud-" + Math.random().toString(36).substring(2, 9),
      brand_id: finding.brand_id,
      at: new Date().toISOString(),
      action: "FINDING_STATUS_UPDATED",
      actor: "analyst",
      details: {
        finding_id: findingId,
        new_status: data.status,
        reason: data.decision_reason,
      },
    });

    return finding;
  },

  async getFindingComparison(findingId) {
    return getMockComparison(findingId);
  },

  async getCleared(_brandId, params) {
    let filtered = [...db.cleared];
    if (params?.decision) filtered = filtered.filter((c) => c.decision === params.decision);
    if (params?.scan_id) {
      filtered = filtered.filter(
        (c) => c.scan_id === params.scan_id || params.scan_id === SCAN_ID || params.scan_id?.startsWith("scan-")
      );
    }
    if (params?.platform) filtered = filtered.filter((c) => c.candidate.platform === params.platform);
    if (params?.q) {
      const q = params.q.toLowerCase();
      filtered = filtered.filter((c) => c.candidate.display_name.toLowerCase().includes(q));
    }

    const offset = params?.offset || 0;
    const limit = params?.limit || 20;
    return {
      items: filtered.slice(offset, offset + limit),
      total: filtered.length,
      limit,
      offset,
    };
  },

  async getAudit(_brandId, params) {
    const offset = params?.offset || 0;
    const limit = params?.limit || 20;
    return {
      items: db.audit.slice(offset, offset + limit),
      total: db.audit.length,
      limit,
      offset,
    };
  },

  // 11.6 Evaluation (Calculated dynamically per Section 14)
  async getEvaluationDatasets() {
    return {
      items: MOCK_DATASETS,
      total: MOCK_DATASETS.length,
    };
  },

  async runEvaluation(data) {
    return computeEvaluationMetrics(MOCK_EVAL_CASES, data.split || "HELDOUT");
  },

  async getEvaluation(_evaluationId) {
    return computeEvaluationMetrics(MOCK_EVAL_CASES, "HELDOUT");
  },

  async getLatestEvaluation(params) {
    return computeEvaluationMetrics(MOCK_EVAL_CASES, params?.split || "HELDOUT");
  },

  // 11.7 P1 endpoints
  async getFindingRelated(_findingId) {
    return {
      items: [],
      total: 0,
      limit: 20,
      offset: 0,
    };
  },

  async createFindingSummary(_findingId) {
    return {
      summary: "Simulated P1 automated narrative summary based on observable signals.",
      generated_by: "template",
    };
  },

  async bulkUpdateFindingStatus(data) {
    let count = 0;
    for (const id of data.finding_ids) {
      const finding = db.findings.find((f) => f.id === id);
      if (finding) {
        finding.status = data.status;
        count++;
      }
    }
    return { updated_count: count };
  },

  async exportFindingsCsv(_brandId) {
    return "id,candidate_name,platform,risk_score,severity,status\n" +
      db.findings
        .map(
          (f) =>
            `"${f.id}","${f.candidate.display_name}","${f.candidate.platform}",${f.risk_score},"${f.severity}","${f.status}"`
        )
        .join("\n");
  },

  async cancelScan(_scanId) {
    return { status: "cancelled" };
  },

  async reopenCleared(_brandId, _assessmentId) {
    return { reopened: true };
  },

  async getFindingReport(findingId) {
    const finding = await this.getFinding(findingId);
    return {
      finding_id: findingId,
      generated_at: new Date().toISOString(),
      evidence_package: {
        candidate: finding.candidate,
        risk_score: finding.risk_score,
        signals: finding.score_breakdown,
        evidence: finding.evidence,
      },
    };
  },
};
