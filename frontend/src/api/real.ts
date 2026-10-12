import { ApiError } from "./errors";
import type { ApiClient, Schema } from "./client";

export function createRealApiClient(rawBaseUrl: string): ApiClient {
  const normalizedBase = rawBaseUrl.replace(/\/+$/, "");
  const apiPrefix = `${normalizedBase}/api/v1`;

  async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const url = `${apiPrefix}${path}`;
    const headers = new Headers(options.headers);
    if (!headers.has("Content-Type") && options.body && typeof options.body === "string") {
      headers.set("Content-Type", "application/json");
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let code: Schema["ApiErrorCode"] = "INTERNAL_ERROR";
      let message = response.statusText || "Request failed";
      let details: Array<{ field?: string; issue: string }> | undefined;
      let requestId = response.headers.get("x-request-id") || "req-unknown";

      try {
        const errorJson = await response.json();
        if (errorJson && errorJson.error) {
          code = errorJson.error.code || code;
          message = errorJson.error.message || message;
          details = errorJson.error.details;
          requestId = errorJson.error.request_id || requestId;
        }
      } catch {
        // Body was not JSON
      }

      throw new ApiError(response.status, {
        code,
        message,
        details,
        request_id: requestId,
      });
    }

    if (response.status === 204) {
      return {} as T;
    }

    return response.json() as Promise<T>;
  }

  function toQuery(params: Record<string, unknown> | undefined): string {
    if (!params) return "";
    const search = new URLSearchParams();
    for (const [key, val] of Object.entries(params)) {
      if (val !== undefined && val !== null) {
        search.set(key, String(val));
      }
    }
    const q = search.toString();
    return q ? `?${q}` : "";
  }

  return {
    // 11.1 Health and meta
    getHealth: () => request<Schema["HealthResponse"]>("/health"),
    getReady: () => request<Schema["ReadyResponse"]>("/ready"),
    getMeta: () => request<Schema["MetaResponse"]>("/meta"),
    getSourcesStatus: (refresh = false) =>
      request<Schema["SourceStatusEntry"][]>(`/sources/status${toQuery({ refresh })}`),

    // 11.2 Brands
    getBrands: (params) => request<Schema["PaginatedBrands"]>(`/brands${toQuery(params)}`),
    createBrand: (data) =>
      request<Schema["Brand"]>("/brands", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    getBrand: (brandId) => request<Schema["Brand"]>(`/brands/${brandId}`),
    patchBrand: (brandId, data) =>
      request<Schema["Brand"]>(`/brands/${brandId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    getBrandSummary: (brandId) =>
      request<Schema["BrandSummary"]>(`/brands/${brandId}/summary`),

    // 11.3 Official assets
    prefillAsset: (brandId, data) =>
      request<Schema["PrefillResponse"]>(`/brands/${brandId}/assets/prefill`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    createAsset: (brandId, data) =>
      request<Schema["OfficialAsset"]>(`/brands/${brandId}/assets`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    getAssets: (brandId, params) =>
      request<Schema["PaginatedOfficialAssets"]>(`/brands/${brandId}/assets${toQuery(params)}`),
    getAsset: (brandId, assetId) =>
      request<Schema["OfficialAsset"]>(`/brands/${brandId}/assets/${assetId}`),
    patchAsset: (brandId, assetId, data) =>
      request<Schema["OfficialAsset"]>(`/brands/${brandId}/assets/${assetId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),

    // 11.4 Scans
    createScan: (data) =>
      request<Schema["ScanCreateResponse"]>("/scans", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    getScan: (scanId) => request<Schema["ScanDetail"]>(`/scans/${scanId}`),
    getScans: (params) => request<Schema["PaginatedScans"]>(`/scans${toQuery(params)}`),
    getScanFindings: (scanId, params) =>
      request<Schema["PaginatedFindings"]>(`/scans/${scanId}/findings${toQuery(params)}`),
    getScanCleared: (scanId, params) =>
      request<Schema["PaginatedCleared"]>(`/scans/${scanId}/cleared${toQuery(params)}`),

    // 11.5 Findings and comparison
    getFindings: (params) =>
      request<Schema["PaginatedFindings"]>(`/findings${toQuery(params)}`),
    getFinding: (findingId) => request<Schema["FindingDetail"]>(`/findings/${findingId}`),
    patchFinding: (findingId, data) =>
      request<Schema["FindingDetail"]>(`/findings/${findingId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    getFindingComparison: (findingId) =>
      request<Schema["FindingComparison"]>(`/findings/${findingId}/comparison`),
    getCleared: (brandId, params) =>
      request<Schema["PaginatedCleared"]>(`/brands/${brandId}/cleared${toQuery(params)}`),
    getAudit: (brandId, params) =>
      request<Schema["PaginatedAudit"]>(`/brands/${brandId}/audit${toQuery(params)}`),

    // 11.6 Evaluation
    getEvaluationDatasets: () =>
      request<Schema["PaginatedEvaluationDatasets"]>("/evaluations/datasets"),
    runEvaluation: (data) =>
      request<Schema["EvaluationResult"]>("/evaluations/run", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    getEvaluation: (evaluationId) =>
      request<Schema["EvaluationResult"]>(`/evaluations/${evaluationId}`),
    getLatestEvaluation: (params) =>
      request<Schema["EvaluationResult"]>(`/evaluations/latest${toQuery(params)}`),

    // 11.7 Reserved P1 endpoints
    getFindingRelated: (findingId) =>
      request<Schema["PaginatedFindings"]>(`/findings/${findingId}/related`),
    createFindingSummary: (findingId) =>
      request<Schema["FindingSummaryP1"]>(`/findings/${findingId}/summary`, {
        method: "POST",
      }),
    bulkUpdateFindingStatus: (data) =>
      request<{ updated_count: number }>("/findings/bulk-status", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    exportFindingsCsv: async (brandId) => {
      const url = `${apiPrefix}/brands/${brandId}/export/findings.csv`;
      const res = await fetch(url);
      if (!res.ok) throw new ApiError(res.status, { code: "INTERNAL_ERROR", message: "Export failed", request_id: "req-export" });
      return res.text();
    },
    cancelScan: (scanId) =>
      request<{ status: "cancelled" }>(`/scans/${scanId}/cancel`, { method: "POST" }),
    reopenCleared: (brandId, assessmentId) =>
      request<{ reopened: boolean }>(`/brands/${brandId}/cleared/${assessmentId}/reopen`, {
        method: "POST",
      }),
    getFindingReport: (findingId) =>
      request<Schema["FindingReport"]>(`/findings/${findingId}/report`),
  };
}
