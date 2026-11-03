import type { Investigation, TransactionResult } from "../types/api";

export function validWebsite(value: string): boolean {
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) && Boolean(url.hostname) && !url.username && !url.password;
  } catch { return false; }
}

export function investigationHref(item: Investigation): string | null {
  if (!item.resource_id) return null;
  const id = encodeURIComponent(item.resource_id);
  if (item.investigation_type.includes("website")) return `/website-scanner/${id}`;
  if (item.investigation_type.includes("upload") || item.investigation_type.includes("batch")) return `/transactions?upload=${id}`;
  if (item.investigation_type.includes("transaction")) return `/transactions/${id}`;
  return null;
}

export function selectTransactions(rows: TransactionResult[], search: string, risk: string, sort: string): TransactionResult[] {
  const query = search.trim().toLowerCase();
  return rows.filter((row) => (!query || `${row.transaction_reference} ${row.id} ${row.amount}`.toLowerCase().includes(query)) && (risk === "all" || row.risk_level === risk))
    .sort((a, b) => sort === "amount" ? b.amount - a.amount : sort === "oldest" ? a.created_at.localeCompare(b.created_at) : sort === "newest" ? b.created_at.localeCompare(a.created_at) : b.fraud_probability - a.fraud_probability);
}
