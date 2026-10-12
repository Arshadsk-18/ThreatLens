import type { components } from "./schema";

export type Schema = components["schemas"];

export interface ApiClient {
  // 11.1 Health and meta
  getHealth(): Promise<Schema["HealthResponse"]>;
  getReady(): Promise<Schema["ReadyResponse"]>;
  getMeta(): Promise<Schema["MetaResponse"]>;
  getSourcesStatus(refresh?: boolean): Promise<Schema["SourceStatusEntry"][]>;

  // 11.2 Brands
  getBrands(params?: { limit?: number; offset?: number }): Promise<Schema["PaginatedBrands"]>;
  createBrand(data: Schema["BrandCreate"]): Promise<Schema["Brand"]>;
  getBrand(brandId: string): Promise<Schema["Brand"]>;
  patchBrand(brandId: string, data: Schema["BrandUpdate"]): Promise<Schema["Brand"]>;
  getBrandSummary(brandId: string): Promise<Schema["BrandSummary"]>;

  // 11.3 Official assets
  prefillAsset(brandId: string, data: Schema["PrefillRequest"]): Promise<Schema["PrefillResponse"]>;
  createAsset(brandId: string, data: Schema["OfficialAssetCreate"]): Promise<Schema["OfficialAsset"]>;
  getAssets(
    brandId: string,
    params?: {
      asset_type?: Schema["AssetType"];
      relationship?: Schema["Relationship"];
      is_verified?: boolean;
      is_active?: boolean;
      limit?: number;
      offset?: number;
    }
  ): Promise<Schema["PaginatedOfficialAssets"]>;
  getAsset(brandId: string, assetId: string): Promise<Schema["OfficialAsset"]>;
  patchAsset(
    brandId: string,
    assetId: string,
    data: Schema["OfficialAssetUpdate"]
  ): Promise<Schema["OfficialAsset"]>;

  // 11.4 Scans
  createScan(data: Schema["ScanCreate"]): Promise<Schema["ScanCreateResponse"]>;
  getScan(scanId: string): Promise<Schema["ScanDetail"]>;
  getScans(params?: {
    brand_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<Schema["PaginatedScans"]>;
  getScanFindings(
    scanId: string,
    params?: { limit?: number; offset?: number }
  ): Promise<Schema["PaginatedFindings"]>;
  getScanCleared(
    scanId: string,
    params?: { limit?: number; offset?: number }
  ): Promise<Schema["PaginatedCleared"]>;

  // 11.5 Findings and comparison
  getFindings(params?: {
    brand_id?: string;
    scan_id?: string;
    status?: Schema["FindingStatus"];
    asset_type?: Schema["AssetType"];
    platform?: string;
    severity?: Schema["Severity"];
    min_score?: number;
    source_mode?: Schema["SourceMode"];
    q?: string;
    latest_only?: boolean;
    include_dismissed?: boolean;
    sort?: "score_desc" | "score_asc" | "seen_desc" | "name_asc";
    limit?: number;
    offset?: number;
  }): Promise<Schema["PaginatedFindings"]>;
  getFinding(findingId: string): Promise<Schema["FindingDetail"]>;
  patchFinding(findingId: string, data: Schema["FindingPatch"]): Promise<Schema["FindingDetail"]>;
  getFindingComparison(findingId: string): Promise<Schema["FindingComparison"]>;
  getCleared(
    brandId: string,
    params?: {
      decision?: Schema["IdentityDecision"];
      scan_id?: string;
      platform?: string;
      q?: string;
      limit?: number;
      offset?: number;
    }
  ): Promise<Schema["PaginatedCleared"]>;
  getAudit(
    brandId: string,
    params?: { limit?: number; offset?: number }
  ): Promise<Schema["PaginatedAudit"]>;

  // 11.6 Evaluation
  getEvaluationDatasets(): Promise<Schema["PaginatedEvaluationDatasets"]>;
  runEvaluation(data: Schema["EvaluationRunRequest"]): Promise<Schema["EvaluationResult"]>;
  getEvaluation(evaluationId: string): Promise<Schema["EvaluationResult"]>;
  getLatestEvaluation(params?: {
    dataset_id?: string;
    split?: Schema["EvalSplit"];
  }): Promise<Schema["EvaluationResult"]>;

  // 11.7 P1 endpoints (typed and exposed per specification)
  getFindingRelated(findingId: string): Promise<Schema["PaginatedFindings"]>;
  createFindingSummary(findingId: string): Promise<Schema["FindingSummaryP1"]>;
  bulkUpdateFindingStatus(data: Schema["BulkStatusRequest"]): Promise<{ updated_count: number }>;
  exportFindingsCsv(brandId: string): Promise<string>;
  cancelScan(scanId: string): Promise<{ status: "cancelled" }>;
  reopenCleared(brandId: string, assessmentId: string): Promise<{ reopened: boolean }>;
  getFindingReport(findingId: string): Promise<Schema["FindingReport"]>;
}

// Client selection rule: if VITE_API_URL is empty -> mock, else real. No other switch.
import { mockApiClient } from "./mock";
import { createRealApiClient } from "./real";

const apiUrl = import.meta.env.VITE_API_URL;
export const apiClient: ApiClient =
  apiUrl && apiUrl.trim() !== "" ? createRealApiClient(apiUrl.trim()) : mockApiClient;
