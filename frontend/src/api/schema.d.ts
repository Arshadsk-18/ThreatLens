/**
 * Schema types for ThreatLens v3 API.
 * Generated from OpenAPI contract per Section 11 of ARCHITECTURE_API_CONTRACT.md.
 * Note: When docs/openapi.snapshot.json is present, this file can be regenerated via `npm run gen:types`.
 */

export interface paths {
  "/health": {
    get: {
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["HealthResponse"];
          };
        };
      };
    };
  };
  "/ready": {
    get: {
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["ReadyResponse"];
          };
        };
      };
    };
  };
  "/meta": {
    get: {
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["MetaResponse"];
          };
        };
      };
    };
  };
  "/sources/status": {
    get: {
      parameters?: {
        query?: {
          refresh?: boolean;
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["SourceStatusEntry"][];
          };
        };
      };
    };
  };
  "/brands": {
    get: {
      parameters?: {
        query?: {
          limit?: number;
          offset?: number;
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["PaginatedBrands"];
          };
        };
      };
    };
    post: {
      requestBody: {
        content: {
          "application/json": components["schemas"]["BrandCreate"];
        };
      };
      responses: {
        201: {
          content: {
            "application/json": components["schemas"]["Brand"];
          };
        };
      };
    };
  };
  "/brands/{brand_id}": {
    get: {
      parameters: {
        path: {
          brand_id: string;
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["Brand"];
          };
        };
      };
    };
    patch: {
      parameters: {
        path: {
          brand_id: string;
        };
      };
      requestBody: {
        content: {
          "application/json": components["schemas"]["BrandUpdate"];
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["Brand"];
          };
        };
      };
    };
  };
  "/brands/{brand_id}/summary": {
    get: {
      parameters: {
        path: {
          brand_id: string;
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["BrandSummary"];
          };
        };
      };
    };
  };
  "/brands/{brand_id}/assets/prefill": {
    post: {
      parameters: {
        path: {
          brand_id: string;
        };
      };
      requestBody: {
        content: {
          "application/json": components["schemas"]["PrefillRequest"];
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["PrefillResponse"];
          };
        };
      };
    };
  };
  "/brands/{brand_id}/assets": {
    get: {
      parameters: {
        path: {
          brand_id: string;
        };
        query?: {
          asset_type?: components["schemas"]["AssetType"];
          relationship?: components["schemas"]["Relationship"];
          is_verified?: boolean;
          is_active?: boolean;
          limit?: number;
          offset?: number;
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["PaginatedOfficialAssets"];
          };
        };
      };
    };
    post: {
      parameters: {
        path: {
          brand_id: string;
        };
      };
      requestBody: {
        content: {
          "application/json": components["schemas"]["OfficialAssetCreate"];
        };
      };
      responses: {
        201: {
          content: {
            "application/json": components["schemas"]["OfficialAsset"];
          };
        };
      };
    };
  };
  "/brands/{brand_id}/assets/{asset_id}": {
    get: {
      parameters: {
        path: {
          brand_id: string;
          asset_id: string;
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["OfficialAsset"];
          };
        };
      };
    };
    patch: {
      parameters: {
        path: {
          brand_id: string;
          asset_id: string;
        };
      };
      requestBody: {
        content: {
          "application/json": components["schemas"]["OfficialAssetUpdate"];
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["OfficialAsset"];
          };
        };
      };
    };
  };
  "/scans": {
    get: {
      parameters?: {
        query?: {
          brand_id?: string;
          limit?: number;
          offset?: number;
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["PaginatedScans"];
          };
        };
      };
    };
    post: {
      requestBody: {
        content: {
          "application/json": components["schemas"]["ScanCreate"];
        };
      };
      responses: {
        202: {
          content: {
            "application/json": components["schemas"]["ScanCreateResponse"];
          };
        };
      };
    };
  };
  "/scans/{scan_id}": {
    get: {
      parameters: {
        path: {
          scan_id: string;
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["ScanDetail"];
          };
        };
      };
    };
  };
  "/scans/{scan_id}/findings": {
    get: {
      parameters: {
        path: {
          scan_id: string;
        };
        query?: {
          limit?: number;
          offset?: number;
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["PaginatedFindings"];
          };
        };
      };
    };
  };
  "/scans/{scan_id}/cleared": {
    get: {
      parameters: {
        path: {
          scan_id: string;
        };
        query?: {
          limit?: number;
          offset?: number;
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["PaginatedCleared"];
          };
        };
      };
    };
  };
  "/findings": {
    get: {
      parameters?: {
        query?: {
          brand_id?: string;
          scan_id?: string;
          status?: components["schemas"]["FindingStatus"];
          asset_type?: components["schemas"]["AssetType"];
          platform?: string;
          severity?: components["schemas"]["Severity"];
          min_score?: number;
          source_mode?: components["schemas"]["SourceMode"];
          q?: string;
          latest_only?: boolean;
          include_dismissed?: boolean;
          sort?: "score_desc" | "score_asc" | "seen_desc" | "name_asc";
          limit?: number;
          offset?: number;
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["PaginatedFindings"];
          };
        };
      };
    };
  };
  "/findings/{finding_id}": {
    get: {
      parameters: {
        path: {
          finding_id: string;
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["FindingDetail"];
          };
        };
      };
    };
    patch: {
      parameters: {
        path: {
          finding_id: string;
        };
      };
      requestBody: {
        content: {
          "application/json": components["schemas"]["FindingPatch"];
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["FindingDetail"];
          };
        };
      };
    };
  };
  "/findings/{finding_id}/comparison": {
    get: {
      parameters: {
        path: {
          finding_id: string;
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["FindingComparison"];
          };
        };
      };
    };
  };
  "/brands/{brand_id}/cleared": {
    get: {
      parameters: {
        path: {
          brand_id: string;
        };
        query?: {
          decision?: components["schemas"]["IdentityDecision"];
          scan_id?: string;
          platform?: string;
          q?: string;
          limit?: number;
          offset?: number;
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["PaginatedCleared"];
          };
        };
      };
    };
  };
  "/brands/{brand_id}/audit": {
    get: {
      parameters: {
        path: {
          brand_id: string;
        };
        query?: {
          limit?: number;
          offset?: number;
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["PaginatedAudit"];
          };
        };
      };
    };
  };
  "/evaluations/datasets": {
    get: {
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["PaginatedEvaluationDatasets"];
          };
        };
      };
    };
  };
  "/evaluations/run": {
    post: {
      requestBody: {
        content: {
          "application/json": components["schemas"]["EvaluationRunRequest"];
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["EvaluationResult"];
          };
        };
      };
    };
  };
  "/evaluations/{evaluation_id}": {
    get: {
      parameters: {
        path: {
          evaluation_id: string;
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["EvaluationResult"];
          };
        };
      };
    };
  };
  "/evaluations/latest": {
    get: {
      parameters?: {
        query?: {
          dataset_id?: string;
          split?: components["schemas"]["EvalSplit"];
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["EvaluationResult"];
          };
        };
      };
    };
  };
  // Reserved P1 endpoints
  "/findings/{finding_id}/related": {
    get: {
      parameters: {
        path: {
          finding_id: string;
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["PaginatedFindings"];
          };
        };
      };
    };
  };
  "/findings/{finding_id}/summary": {
    post: {
      parameters: {
        path: {
          finding_id: string;
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["FindingSummaryP1"];
          };
        };
      };
    };
  };
  "/findings/bulk-status": {
    post: {
      requestBody: {
        content: {
          "application/json": components["schemas"]["BulkStatusRequest"];
        };
      };
      responses: {
        200: {
          content: {
            "application/json": { updated_count: number };
          };
        };
      };
    };
  };
  "/brands/{brand_id}/export/findings.csv": {
    get: {
      parameters: {
        path: {
          brand_id: string;
        };
      };
      responses: {
        200: {
          content: {
            "text/csv": string;
          };
        };
      };
    };
  };
  "/scans/{scan_id}/cancel": {
    post: {
      parameters: {
        path: {
          scan_id: string;
        };
      };
      responses: {
        200: {
          content: {
            "application/json": { status: "cancelled" };
          };
        };
      };
    };
  };
  "/brands/{brand_id}/cleared/{assessment_id}/reopen": {
    post: {
      parameters: {
        path: {
          brand_id: string;
          assessment_id: string;
        };
      };
      responses: {
        200: {
          content: {
            "application/json": { reopened: boolean };
          };
        };
      };
    };
  };
  "/findings/{finding_id}/report": {
    get: {
      parameters: {
        path: {
          finding_id: string;
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["FindingReport"];
          };
        };
      };
    };
  };
}

export interface components {
  schemas: {
    // Enums
    ScanMode: "LIVE" | "DEMO";
    SourceMode: "LIVE" | "CACHED" | "SIMULATED";
    SourceStatus: "CONNECTED" | "PARTIAL" | "NOT_CONNECTED" | "RATE_LIMITED" | "ERROR";
    ScanStatus: "QUEUED" | "RUNNING" | "COMPLETED" | "COMPLETED_WITH_ERRORS" | "FAILED";
    ScanStage:
      | "queued"
      | "resolving_brand"
      | "planning_queries"
      | "fetching"
      | "normalizing"
      | "hashing_images"
      | "assessing"
      | "persisting"
      | "completed"
      | "failed";
    AssetType: "IOS_APP" | "ANDROID_APP" | "SOCIAL_ACCOUNT";
    Relationship: "OFFICIAL" | "AUTHORIZED_PARTNER";
    VerificationMethod: "OWNER_PROVIDED" | "STORE_LOOKUP" | "DOMAIN_VERIFIED_HANDLE";
    IdentityDecision:
      | "OFFICIAL_EXACT_MATCH"
      | "OFFICIAL_PUBLISHER_MATCH"
      | "AUTHORIZED_PARTNER_MATCH"
      | "BENIGN_LOOKALIKE"
      | "BELOW_THRESHOLD"
      | "CANDIDATE_FOR_REVIEW";
    Severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
    FindingStatus:
      | "NEW"
      | "IN_REVIEW"
      | "CONFIRMED_SUSPICIOUS"
      | "DISMISSED_FALSE_POSITIVE"
      | "INCONCLUSIVE";
    EvidenceStatus: "OBSERVED" | "INFERRED" | "UNAVAILABLE" | "SIMULATED";
    EvidenceGroup: "NAME" | "IDENTITY" | "VISUAL" | "CONTENT" | "CONTEXT";
    LookalikeTechnique:
      | "EXACT_NAME_REUSE"
      | "HOMOGLYPH"
      | "CHARACTER_SWAP"
      | "OMISSION"
      | "REPETITION"
      | "KEYBOARD_ADJACENT"
      | "ADDED_WORD"
      | "SPACING"
      | "SEPARATOR"
      | "NONE";
    ProviderErrorCode:
      | "TIMEOUT"
      | "RATE_LIMITED"
      | "AUTH_REQUIRED"
      | "PROVIDER_UNAVAILABLE"
      | "NOT_CONFIGURED"
      | "INVALID_RESPONSE"
      | "BLOCKED_URL";
    ApiErrorCode:
      | "VALIDATION_ERROR"
      | "NOT_FOUND"
      | "CONFLICT"
      | "SCAN_ALREADY_RUNNING"
      | "MODE_NOT_ALLOWED"
      | "RATE_LIMITED"
      | "UNAUTHORIZED"
      | "INTERNAL_ERROR";
    EvalLabel: "IMPERSONATION" | "BENIGN_NAMESAKE" | "OFFICIAL";
    EvalProvenance: "REAL_CAPTURED" | "SYNTHETIC";
    EvalSplit: "DEV" | "HELDOUT";

    // Error
    ApiErrorEnvelope: {
      error: {
        code: components["schemas"]["ApiErrorCode"];
        message: string;
        details?: Array<{ field?: string; issue: string }>;
        request_id: string;
      };
    };

    // Health & Meta
    HealthResponse: {
      status: string;
      service: string;
      version: string;
      contract_version: string;
    };
    ReadyResponse: {
      ready: boolean;
      checks: {
        database: string;
        config: string;
      };
    };
    MetaResponse: {
      scoring_version: string;
      relevance_threshold: number;
      review_threshold: number;
      severity_bands: Record<string, [number, number]>;
      enums: Record<string, string[]>;
      supported_platforms: string[];
      supported_asset_types: string[];
    };
    SourceStatusEntry: {
      source_id: string;
      display_name: string;
      platform: string;
      asset_types: components["schemas"]["AssetType"][];
      status: components["schemas"]["SourceStatus"];
      supported_modes: components["schemas"]["SourceMode"][];
      default_mode: components["schemas"]["SourceMode"];
      last_checked_at: string | null;
      rate_limit_note: string | null;
      message: string;
    };

    // Brands
    Brand: {
      id: string;
      name: string;
      description: string;
      official_domains: string[];
      keywords: string[];
      distinctive_tokens: string[];
      industry_category: string;
      demo_brand: boolean;
      created_at: string;
      updated_at: string;
    };
    BrandCreate: {
      name: string;
      description: string;
      official_domains: string[];
      keywords: string[];
      distinctive_tokens: string[];
      industry_category: string;
      demo_brand?: boolean;
    };
    BrandUpdate: {
      name?: string;
      description?: string;
      official_domains?: string[];
      keywords?: string[];
      distinctive_tokens?: string[];
      industry_category?: string;
    };
    BrandSummary: {
      brand_id: string;
      official_asset_count: number;
      last_scan: {
        id: string;
        mode: components["schemas"]["ScanMode"];
        status: components["schemas"]["ScanStatus"];
        completed_at: string | null;
      } | null;
      funnel: components["schemas"]["FunnelCounts"];
      findings_by_severity: Record<components["schemas"]["Severity"], number>;
      findings_by_status: Record<components["schemas"]["FindingStatus"], number>;
      findings_by_platform: Record<string, number>;
      cleared_by_decision: Record<components["schemas"]["IdentityDecision"], number>;
      review_progress: {
        reviewed: number;
        total: number;
      };
      source_coverage: Array<{
        source_id: string;
        status: components["schemas"]["SourceStatus"];
        source_mode: components["schemas"]["SourceMode"] | null;
        retrieved_at: string | null;
      }>;
      latest_evaluation: {
        id: string | null;
        split: components["schemas"]["EvalSplit"] | null;
        precision: number | null;
        recall: number | null;
        created_at: string | null;
      } | null;
    };
    FunnelCounts: {
      retrieved: number;
      deduplicated: number;
      official_cleared: number;
      not_relevant: number;
      benign_lookalike: number;
      below_threshold: number;
      findings: number;
    };

    // Official Assets
    PrefillRequest:
      | { url: string; platform?: never; identifier?: never }
      | { platform: string; identifier: string; url?: never };
    AssetDraft: {
      asset_type: components["schemas"]["AssetType"];
      platform: string;
      stable_identifier: string;
      secondary_identifiers?: Record<string, string>;
      developer_id: string | null;
      publisher_name: string | null;
      display_name: string;
      description: string;
      category: string;
      canonical_url: string;
      icon_url: string | null;
      verification_method: components["schemas"]["VerificationMethod"];
      relationship: components["schemas"]["Relationship"];
      trust_publisher: boolean;
    };
    PrefillResponse: {
      source_id: string;
      source_mode: components["schemas"]["SourceMode"];
      retrieved_at: string;
      draft: components["schemas"]["AssetDraft"] | null;
      source_status?: components["schemas"]["SourceStatus"];
      error_code?: components["schemas"]["ProviderErrorCode"] | null;
      message?: string;
    };
    OfficialAsset: {
      id: string;
      brand_id: string;
      asset_type: components["schemas"]["AssetType"];
      platform: string;
      stable_identifier: string;
      secondary_identifiers?: Record<string, string>;
      developer_id: string | null;
      publisher_name: string | null;
      display_name: string;
      handle: string | null;
      description: string;
      category: string;
      canonical_url: string;
      icon_url: string | null;
      icon_hash?: string | null;
      relationship: components["schemas"]["Relationship"];
      verification_method: components["schemas"]["VerificationMethod"];
      is_verified: boolean;
      trust_publisher: boolean;
      is_active: boolean;
      notes: string;
      warning?: string | null;
      created_at: string;
      updated_at: string;
    };
    OfficialAssetCreate: {
      asset_type: components["schemas"]["AssetType"];
      platform: string;
      stable_identifier: string;
      secondary_identifiers?: Record<string, string>;
      developer_id?: string | null;
      publisher_name?: string | null;
      display_name: string;
      handle?: string | null;
      description?: string;
      category?: string;
      canonical_url: string;
      icon_url?: string | null;
      relationship: components["schemas"]["Relationship"];
      verification_method: components["schemas"]["VerificationMethod"];
      is_verified?: boolean;
      trust_publisher?: boolean;
      notes?: string;
    };
    OfficialAssetUpdate: {
      display_name?: string;
      description?: string;
      is_active?: boolean;
      trust_publisher?: boolean;
      notes?: string;
    };

    // Scans
    ScanCreate: {
      brand_id: string;
      mode: components["schemas"]["ScanMode"];
      asset_types?: components["schemas"]["AssetType"][];
      source_ids?: string[];
      query_limit_per_source?: number;
      include_icon_similarity?: boolean;
      force_refresh?: boolean;
      allow_stale_cache?: boolean;
    };
    ScanCreateResponse: {
      id: string;
      brand_id: string;
      mode: components["schemas"]["ScanMode"];
      status: components["schemas"]["ScanStatus"];
      stage: components["schemas"]["ScanStage"];
      progress_percent: number;
      created_at: string;
    };
    ScanDetail: {
      id: string;
      brand_id: string;
      mode: components["schemas"]["ScanMode"];
      status: components["schemas"]["ScanStatus"];
      stage: components["schemas"]["ScanStage"];
      progress_percent: number;
      options: {
        asset_types: components["schemas"]["AssetType"][];
        source_ids: string[];
        query_limit_per_source: number;
        include_icon_similarity: boolean;
        force_refresh: boolean;
        allow_stale_cache: boolean;
      };
      source_outcomes: components["schemas"]["SourceOutcome"][];
      funnel: components["schemas"]["FunnelCounts"];
      findings_by_severity: Record<components["schemas"]["Severity"], number>;
      events: components["schemas"]["ScanEvent"][];
      error_message: string | null;
      created_at: string;
      started_at: string | null;
      completed_at: string | null;
    };
    SourceOutcome: {
      source_id: string;
      status: components["schemas"]["SourceStatus"];
      source_mode: components["schemas"]["SourceMode"] | null;
      queries_planned: number;
      queries_executed: number;
      candidate_count: number;
      cache_hit_count: number;
      error_code: components["schemas"]["ProviderErrorCode"] | null;
      message: string;
      retrieved_at: string | null;
      duration_ms: number;
    };
    ScanEvent: {
      at: string;
      stage: components["schemas"]["ScanStage"];
      source_id: string | null;
      level: "INFO" | "WARNING" | "ERROR";
      message: string;
    };
    ScanSummaryItem: {
      id: string;
      brand_id: string;
      mode: components["schemas"]["ScanMode"];
      status: components["schemas"]["ScanStatus"];
      stage: components["schemas"]["ScanStage"];
      progress_percent: number;
      findings_count: number;
      cleared_count: number;
      created_at: string;
      completed_at: string | null;
    };

    // Findings
    FindingCandidate: {
      platform: string;
      asset_type: components["schemas"]["AssetType"];
      stable_identifier: string;
      display_name: string;
      handle: string | null;
      publisher_name: string | null;
      developer_id?: string | null;
      icon_url: string | null;
      canonical_url: string;
      description?: string;
      category?: string;
      external_links?: string[];
      created_at_source?: string | null;
      followers?: number | null;
      rating_count?: number | null;
    };
    TopSignal: {
      signal: string;
      points: number;
      max_points: number;
      reason: string;
    };
    FindingListItem: {
      id: string;
      brand_id: string;
      scan_id: string;
      candidate: components["schemas"]["FindingCandidate"];
      risk_score: number;
      severity: components["schemas"]["Severity"];
      evidence_coverage: number;
      technique: components["schemas"]["LookalikeTechnique"];
      top_signals: components["schemas"]["TopSignal"][];
      status: components["schemas"]["FindingStatus"];
      source_mode: components["schemas"]["SourceMode"];
      observed_at: string;
      changed_since_decision: boolean;
    };
    ScoreBreakdownItem: {
      signal: string;
      group: components["schemas"]["EvidenceGroup"];
      value: number;
      points: number;
      max_points: number;
      status: components["schemas"]["EvidenceStatus"];
      reason: string;
      detail: Record<string, unknown>;
    };
    EvidenceItem: {
      id: string;
      evidence_type: string;
      source_id: string;
      status: components["schemas"]["EvidenceStatus"];
      observed_at: string;
      field_name: string;
      observed_value: string;
      source_url: string;
      notes: string;
    };
    FindingDetail: components["schemas"]["FindingListItem"] & {
      identity_guard: {
        decision: components["schemas"]["IdentityDecision"];
        rule: string;
        matched_official_asset_id: string | null;
        explanation: string;
      };
      corroborating_groups: components["schemas"]["EvidenceGroup"][];
      gates_applied: string[];
      score_breakdown: components["schemas"]["ScoreBreakdownItem"][];
      evidence: components["schemas"]["EvidenceItem"][];
      explanation: string;
      limitations: string[];
      scoring_version: string;
      decision_history: Array<{
        at: string;
        status: components["schemas"]["FindingStatus"];
        reason?: string;
        notes?: string;
      }>;
      created_at: string;
    };
    FindingPatch: {
      status: components["schemas"]["FindingStatus"];
      decision_reason?: string;
      notes?: string;
    };
    DiffSegment: {
      text: string;
      changed: boolean;
    };
    NonAsciiChar: {
      char: string;
      codepoint: string;
      index: number;
    };
    FindingComparison: {
      finding_id: string;
      nearest_official_asset_id: string | null;
      official_asset: {
        asset_id: string;
        display_name: string;
        stable_identifier: string;
        publisher_name: string | null;
        developer_id: string | null;
        category: string;
        icon_url: string | null;
        canonical_url: string;
      } | null;
      candidate_asset: {
        display_name: string;
        stable_identifier: string;
        publisher_name: string | null;
        developer_id: string | null;
        category: string;
        icon_url: string | null;
        canonical_url: string;
      };
      comparisons: Array<{
        field: string;
        official_value: string | null;
        candidate_value: string | null;
        similarity: number | null;
        name_diff?: components["schemas"]["DiffSegment"][];
        non_ascii_chars?: components["schemas"]["NonAsciiChar"][];
        detail?: Record<string, unknown>;
      }>;
      disclaimer: string;
    };

    // Cleared
    ClearedItem: {
      id: string;
      scan_id: string;
      candidate: {
        platform: string;
        asset_type: components["schemas"]["AssetType"];
        stable_identifier: string;
        display_name: string;
        publisher_name: string | null;
        icon_url: string | null;
      };
      decision: components["schemas"]["IdentityDecision"];
      rule: string;
      matched_official_asset_id: string | null;
      explanation: string;
      risk_score: number | null;
      source_mode: components["schemas"]["SourceMode"];
      observed_at: string;
    };

    // Audit
    AuditEvent: {
      id: string;
      brand_id: string;
      at: string;
      action: string;
      actor: string;
      details: Record<string, unknown>;
    };

    // Evaluation
    EvaluationDataset: {
      dataset_id: string;
      case_count: number;
      by_label: Record<components["schemas"]["EvalLabel"], number>;
      by_provenance: Record<components["schemas"]["EvalProvenance"], number>;
      by_split: Record<components["schemas"]["EvalSplit"], number>;
      description: string;
      limitations: string[];
    };
    EvaluationRunRequest: {
      dataset_id: string;
      split: components["schemas"]["EvalSplit"];
      include_baseline?: boolean;
      include_ablation?: boolean;
    };
    EvaluationResult: {
      id: string;
      dataset_id: string;
      split: components["schemas"]["EvalSplit"];
      scoring_version: string;
      threshold: { review: number };
      sample_count: number;
      confusion: {
        tp: number;
        fp: number;
        tn: number;
        fn: number;
      };
      precision: number | null;
      recall: number | null;
      f1: number | null;
      false_positive_rate: number | null;
      confidence_intervals: {
        precision: [number, number] | null;
        recall: [number, number] | null;
        false_positive_rate: [number, number] | null;
        method: string;
      };
      official_flagged_count: number;
      hard_negatives: {
        tested: number;
        correctly_cleared: number;
        false_positives: number;
      };
      technique_recall: Array<{
        technique: components["schemas"]["LookalikeTechnique"];
        tested: number;
        detected: number;
      }>;
      baseline: {
        name: string;
        tuned_on: string;
        precision: number;
        recall: number;
        false_positive_rate: number;
      };
      ablation: Array<{
        configuration: string;
        precision: number;
        recall: number;
        official_flagged_count?: number;
      }>;
      failure_cases: Array<{
        case_id: string;
        expected: string;
        got: string;
        why: string;
      }>;
      definitions: string;
      limitations: string[];
      created_at: string;
    };

    // P1
    FindingSummaryP1: {
      summary: string;
      generated_by: "llm" | "template";
    };
    BulkStatusRequest: {
      finding_ids: string[];
      status: components["schemas"]["FindingStatus"];
      decision_reason?: string;
    };
    FindingReport: {
      finding_id: string;
      generated_at: string;
      evidence_package: Record<string, unknown>;
    };

    // Pagination Wrappers
    PaginatedBrands: {
      items: components["schemas"]["Brand"][];
      total: number;
      limit: number;
      offset: number;
    };
    PaginatedOfficialAssets: {
      items: components["schemas"]["OfficialAsset"][];
      total: number;
      limit: number;
      offset: number;
    };
    PaginatedScans: {
      items: components["schemas"]["ScanSummaryItem"][];
      total: number;
      limit: number;
      offset: number;
    };
    PaginatedFindings: {
      items: components["schemas"]["FindingListItem"][];
      total: number;
      limit: number;
      offset: number;
    };
    PaginatedCleared: {
      items: components["schemas"]["ClearedItem"][];
      total: number;
      limit: number;
      offset: number;
    };
    PaginatedAudit: {
      items: components["schemas"]["AuditEvent"][];
      total: number;
      limit: number;
      offset: number;
    };
    PaginatedEvaluationDatasets: {
      items: components["schemas"]["EvaluationDataset"][];
      total: number;
    };
  };
}
