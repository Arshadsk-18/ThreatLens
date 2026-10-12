import type { components } from "./schema";

export type ApiErrorCode = components["schemas"]["ApiErrorCode"];

export class ApiError extends Error {
  readonly code: ApiErrorCode;
  readonly details?: Array<{ field?: string; issue: string }>;
  readonly request_id: string;
  readonly status: number;

  constructor(
    status: number,
    payload: {
      code: ApiErrorCode;
      message: string;
      details?: Array<{ field?: string; issue: string }>;
      request_id: string;
    }
  ) {
    super(payload.message || `API Error ${status} (${payload.code})`);
    this.name = "ApiError";
    this.status = status;
    this.code = payload.code;
    this.details = payload.details;
    this.request_id = payload.request_id;
  }

  get requestId(): string {
    return this.request_id;
  }
}
