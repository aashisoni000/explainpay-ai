import type { Investigation, ModelMetrics, Report, SystemStatus, TransactionResult, TransactionUpload, UploadDetail, WebsiteScan } from "../types/api";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

export class ApiError extends Error {
  public readonly status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function errorDetail(body: unknown, fallback: string): string {
  if (typeof body === "object" && body !== null && "detail" in body && typeof body.detail === "string") return body.detail;
  return fallback;
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...init, cache: "no-store" });
  } catch {
    throw new ApiError("Cannot reach the ExplainPay API. Check the API connection and try again.", 0);
  }
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    throw new ApiError(errorDetail(body, `Request failed (${response.status} ${response.statusText}).`), response.status);
  }
  return response.json() as Promise<T>;
}

function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}

export const api = {
  health: () => request<{ status: "ok" }>("/api/health"),
  status: () => request<SystemStatus>("/api/system/status"),
  metrics: () => request<ModelMetrics>("/api/transactions/metrics"),
  uploads: () => request<TransactionUpload[]>("/api/transactions/history"),
  upload: (id: string) => request<UploadDetail>(`/api/transactions/uploads/${encodeURIComponent(id)}`),
  analyze: (upload_id: string) => post<UploadDetail>("/api/transactions/analyze", { upload_id }),
  transaction: (id: string) => request<TransactionResult>(`/api/transactions/${encodeURIComponent(id)}`),
  predict: (features: Record<string, number>, merchant_url?: string) => post<TransactionResult>("/predict", { features, ...(merchant_url ? { merchant_url } : {}) }),
  scan: (url: string) => post<WebsiteScan>("/api/websites/scan", { url }),
  scans: () => request<WebsiteScan[]>("/api/websites/history"),
  website: (id: string) => request<WebsiteScan>(`/api/websites/${encodeURIComponent(id)}`),
  investigations: () => request<Investigation[]>("/api/investigations"),
  investigation: (id: string) => request<Investigation>(`/api/investigations/${encodeURIComponent(id)}`),
  reports: () => request<Report[]>("/api/reports"),
  generateReport: (investigation_id: string) => post<Report>("/api/reports/generate", { investigation_id }),
};

export function uploadFile(file: File, onProgress: (progress: number) => void): Promise<TransactionUpload> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_URL}/api/transactions/upload`);
    xhr.timeout = 120_000;
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
    };
    xhr.onerror = () => reject(new ApiError("Upload failed. Check your API connection.", 0));
    xhr.ontimeout = () => reject(new ApiError("Upload timed out. Try again.", 0));
    xhr.onabort = () => reject(new ApiError("Upload cancelled.", 0));
    xhr.onload = () => {
      let body: unknown;
      try { body = JSON.parse(xhr.responseText); } catch { reject(new ApiError("The API returned an invalid upload response.", xhr.status)); return; }
      if (xhr.status < 200 || xhr.status >= 300) {
        reject(new ApiError(errorDetail(body, `Upload failed (${xhr.status}).`), xhr.status));
      } else {
        onProgress(100);
        resolve(body as TransactionUpload);
      }
    };
    const form = new FormData();
    form.append("file", file);
    xhr.send(form);
  });
}

export async function downloadReport(id: string): Promise<void> {
  let response: Response;
  try { response = await fetch(`${API_URL}/api/reports/${encodeURIComponent(id)}/download`, { cache: "no-store" }); }
  catch { throw new ApiError("Cannot reach the API to download this report.", 0); }
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    throw new ApiError(errorDetail(body, `Report download failed (${response.status}).`), response.status);
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `explainpay-report-${id}.pdf`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
