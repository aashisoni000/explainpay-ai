"use client";
import Link from "next/link";
import { useState } from "react";
import { api, downloadReport } from "@/lib/api";
import { buttonClass, ErrorNotice, message } from "./ui";

export function ReportActions({ investigationId }: { investigationId: string }) {
  const [busy, setBusy] = useState(false);
  const [reportId, setReportId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  async function generate() {
    setBusy(true); setError(null);
    try { setReportId((await api.generateReport(investigationId)).id); }
    catch (cause) { setError(message(cause)); }
    finally { setBusy(false); }
  }
  async function download() {
    if (!reportId) return;
    setBusy(true); setError(null);
    try { await downloadReport(reportId); }
    catch (cause) { setError(message(cause)); }
    finally { setBusy(false); }
  }
  return <section className="my-6"><div className="flex flex-wrap gap-3"><button className={buttonClass} disabled={busy} onClick={generate}>{busy ? "Working…" : "Generate PDF report"}</button>{reportId && <button className={buttonClass} disabled={busy} onClick={download}>Download report</button>}<Link className={buttonClass} href="/reports">All reports</Link></div>{reportId && <p role="status" className="mt-3 text-xs text-zinc-400">Report generated and saved. Ready to download.</p>}<ErrorNotice error={error} /></section>;
}
