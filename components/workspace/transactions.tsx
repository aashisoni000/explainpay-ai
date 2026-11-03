"use client";

import Link from "next/link";
import { useCallback, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { UploadCloud } from "lucide-react";
import { api, uploadFile } from "@/lib/api";
import { selectTransactions } from "@/lib/workspace";
import type { TransactionResult, UploadDetail } from "@/types/api";
import { Badge, buttonClass, cellClass, date, Empty, ErrorNotice, inputClass, Loading, message, PageTitle, panelClass, percent, Stats, useResource } from "./ui";
import { ReportActions } from "./report-actions";

function UploadPicker({ onUploaded }: { onUploaded: (id: string) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  function choose(candidate?: File) {
    if (!candidate || busy) return;
    setError(null);
    if (!candidate.name.toLowerCase().endsWith(".csv")) { setFile(null); setError("Choose a CSV file. Other formats are not supported."); return; }
    if (!candidate.size) { setFile(null); setError("This file is empty. Choose a CSV with transaction records."); return; }
    setFile(candidate); setProgress(0);
  }
  async function upload() {
    if (!file) return;
    setBusy(true); setError(null); setProgress(0);
    try { onUploaded((await uploadFile(file, setProgress)).id); }
    catch (cause) { setError(message(cause)); }
    finally { setBusy(false); }
  }
  return <section className={`${panelClass} mb-6`}><h2 className="text-lg font-medium">Upload transactions</h2><p className="mt-2 text-sm text-zinc-500">Upload your CSV, inspect the preview, then explicitly run analysis.</p><div onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); if (event.dataTransfer.files.length > 1) { setError("Upload one CSV at a time."); return; } choose(event.dataTransfer.files[0]); }} className={`mt-5 rounded-lg border border-dashed p-7 text-center ${dragging ? "border-white bg-white/10" : "border-white/25"}`}><UploadCloud aria-hidden="true" size={26} className="mx-auto mb-3 text-zinc-400" /><p className="mb-3 text-sm text-zinc-400">Drop a transaction CSV here, or choose a file</p><input ref={input} aria-label="Transaction CSV" type="file" accept=".csv,text/csv" className="sr-only" disabled={busy} onChange={(event) => choose(event.target.files?.[0])} /><button className={buttonClass} disabled={busy} onClick={() => input.current?.click()}>Choose CSV</button>{file && <p className="mt-3 break-all text-xs text-zinc-400">{file.name} · {(file.size / 1024).toFixed(1)} KB</p>}</div><div className="mt-4 flex flex-wrap items-center gap-4"><button className={`${buttonClass} bg-white text-black hover:bg-zinc-200`} disabled={!file || busy} onClick={upload}>{busy ? "Uploading…" : "Upload & preview"}</button>{busy && <div className="min-w-40 flex-1"><label htmlFor="upload-progress" className="mb-2 block text-xs text-zinc-400">{progress === 100 ? "Upload sent; waiting for server…" : `Uploading ${progress}%`}</label><progress id="upload-progress" max={100} value={progress} className="h-2 w-full accent-white" /></div>}</div><ErrorNotice error={error} /></section>;
}

function ResultTable({ rows }: { rows: TransactionResult[] }) {
  const [search, setSearch] = useState("");
  const [risk, setRisk] = useState("all");
  const [sort, setSort] = useState("risk");
  const [page, setPage] = useState(1);
  const filtered = selectTransactions(rows, search, risk, sort);
  const pages = Math.max(1, Math.ceil(filtered.length / 10));
  const currentPage = Math.min(page, pages);
  const start = (currentPage - 1) * 10;
  return <section className="mt-7"><h2 className="mb-4 text-lg font-medium">Transaction results</h2><div className="mb-4 grid gap-3 sm:grid-cols-3"><label className="text-xs text-zinc-500">Search transactions<input className={`${inputClass} mt-2`} placeholder="Reference, ID, or amount" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} /></label><label className="text-xs text-zinc-500">Risk level<select className={`${inputClass} mt-2`} value={risk} onChange={(event) => { setRisk(event.target.value); setPage(1); }}><option value="all">All risk levels</option>{[...new Set(rows.map((row) => row.risk_level))].sort().map((level) => <option key={level}>{level}</option>)}</select></label><label className="text-xs text-zinc-500">Sort results<select className={`${inputClass} mt-2`} value={sort} onChange={(event) => { setSort(event.target.value); setPage(1); }}><option value="risk">Highest probability</option><option value="amount">Highest amount</option><option value="newest">Newest first</option><option value="oldest">Oldest first</option></select></label></div>{!filtered.length ? <Empty>No transactions match your filters.</Empty> : <div className="overflow-x-auto rounded-lg border border-white/15"><table className="w-full"><caption className="sr-only">Analyzed transactions, page {currentPage} of {pages}</caption><thead className="bg-white/5 text-zinc-400"><tr>{["Reference", "Amount¹", "Fraud probability", "Risk", "Prediction", "Detail"].map((label) => <th key={label} scope="col" className={cellClass}>{label}</th>)}</tr></thead><tbody>{filtered.slice(start, start + 10).map((row) => <tr key={row.id} className="hover:bg-white/3"><td className={`${cellClass} font-mono text-xs`}>{row.transaction_reference || row.id}</td><td className={cellClass}>{row.amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td><td className={cellClass}>{percent(row.fraud_probability)}</td><td className={cellClass}><Badge>{row.risk_level}</Badge></td><td className={cellClass}>{row.prediction === 1 ? "Flagged" : "Legitimate"}</td><td className={cellClass}><Link className="underline underline-offset-4" href={`/transactions/${encodeURIComponent(row.id)}`}>Explain<span className="sr-only"> {row.transaction_reference || row.id}</span></Link></td></tr>)}</tbody></table></div>}<div className="mt-4 flex flex-wrap items-center justify-between gap-3"><p className="text-xs text-zinc-500">{filtered.length} matching records · Page {currentPage} / {pages}</p><div className="flex gap-2"><button className={buttonClass} disabled={currentPage === 1} onClick={() => setPage(currentPage - 1)}>Previous</button><button className={buttonClass} disabled={currentPage >= pages} onClick={() => setPage(currentPage + 1)}>Next</button></div></div><p className="mt-3 text-xs text-zinc-600">¹ Amounts are shown as supplied. The dataset does not identify a currency.</p></section>;
}

function ResultCharts({ detail }: { detail: UploadDetail }) {
  const rows = detail.results ?? [];
  const groups = [...new Set(rows.map((row) => row.risk_level))].map((level) => ({ level, count: rows.filter((row) => row.risk_level === level).length }));
  const importance = [...(detail.feature_importance ?? [])].sort((a, b) => b.importance - a.importance).slice(0, 10);
  const max = Math.max(...importance.map((item) => Math.abs(item.importance)), 0.000001);
  return <div className="grid gap-4 lg:grid-cols-2"><section className={panelClass}><h3 className="mb-5 text-sm font-medium">Risk distribution</h3>{groups.map(({ level, count }) => <div key={level} className="mb-4"><div className="mb-2 flex justify-between text-xs text-zinc-400"><span>{level}</span><span>{count} / {rows.length}</span></div><div aria-hidden="true" className="h-2 rounded bg-white/5"><div className="h-full rounded bg-white/60" style={{ width: `${count / rows.length * 100}%` }} /></div></div>)}{!groups.length && <Empty>No analyzed results yet.</Empty>}</section><section className={panelClass}><h3 className="mb-5 text-sm font-medium">Top feature importance</h3>{importance.map((item) => <div key={item.feature} className="mb-3"><div className="mb-1 flex justify-between text-xs text-zinc-400"><span>{item.feature}</span><span>{item.importance.toFixed(5)}</span></div><div aria-hidden="true" className="h-2 bg-white/5"><div className="h-full bg-sky-300/60" style={{ width: `${Math.abs(item.importance) / max * 100}%` }} /></div></div>)}{!importance.length && <Empty>No feature importance returned.</Empty>}</section></div>;
}

function UploadView({ id }: { id: string }) {
  const load = useCallback(() => api.upload(id), [id]);
  const resource = useResource(load);
  const [analyzed, setAnalyzed] = useState<UploadDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const detail = analyzed ?? resource.data;
  async function analyze() {
    setBusy(true); setError(null);
    try { setAnalyzed(await api.analyze(id)); }
    catch (cause) { setError(message(cause)); }
    finally { setBusy(false); }
  }
  if (resource.loading) return <Loading />;
  if (resource.error) return <ErrorNotice error={resource.error} retry={resource.reload} />;
  if (!detail) return null;
  return <section className="mb-10"><div className="mb-5 flex flex-wrap items-center justify-between gap-3"><div><h2 className="break-all text-xl">{detail.filename}</h2><p className="mt-2 text-xs text-zinc-500">{detail.total_records} records · {detail.processed_records} processed · {detail.status}</p></div><button className={buttonClass} disabled={busy} onClick={analyze}>{busy ? "Analyzing…" : detail.results?.length ? "Run analysis again" : "Analyze transactions"}</button></div><ErrorNotice error={error} /><details className={`${panelClass} mb-6`} open={!detail.results?.length}><summary className="cursor-pointer text-sm">CSV preview · {detail.preview.length} rows</summary>{detail.preview.length ? <div className="mt-4 overflow-x-auto"><table className="w-full"><thead><tr>{detail.columns.map((column) => <th scope="col" key={column} className={cellClass}>{column}</th>)}</tr></thead><tbody>{detail.preview.map((row, index) => <tr key={index}>{detail.columns.map((column) => <td className={cellClass} key={column}>{String(row[column] ?? "—")}</td>)}</tr>)}</tbody></table></div> : <p className="mt-3 text-sm text-zinc-500">No preview rows were returned.</p>}</details>{detail.summary && <Stats items={[{ label: "Total analyzed", value: detail.summary.total }, { label: "Flagged", value: detail.summary.flagged }, { label: "Legitimate", value: detail.summary.legitimate }, { label: "High risk", value: detail.summary.high_risk }]} />}{detail.results?.length ? <><ResultCharts detail={detail} /><ResultTable rows={detail.results} /></> : <Empty>No analyzed results yet. Run analysis to see predictions and explanations.</Empty>}{detail.investigation_id && <ReportActions investigationId={detail.investigation_id} />}</section>;
}

export function TransactionsPage() {
  const router = useRouter();
  const query = useSearchParams();
  const id = query.get("upload");
  const history = useResource(api.uploads);
  return <><PageTitle eyebrow="Transaction intelligence" title="Follow the signal." description="Analyze transaction files with the fraud model. Review the evidence behind every prediction before taking action." /><UploadPicker onUploaded={(uploadId) => { router.push(`/transactions?upload=${encodeURIComponent(uploadId)}`); history.reload(); }} />{id && <UploadView key={id} id={id} />}<section><div className="mb-5 flex items-center justify-between"><h2 className="text-lg font-medium">Upload history</h2><button className={buttonClass} onClick={history.reload} disabled={history.loading}>Refresh</button></div>{history.loading ? <Loading /> : <><ErrorNotice error={history.error} retry={history.reload} />{history.data && (history.data.length ? <div className="divide-y divide-white/10 rounded-lg border border-white/15">{history.data.map((upload) => <Link key={upload.id} href={`/transactions?upload=${encodeURIComponent(upload.id)}`} className="flex flex-wrap justify-between gap-3 p-5 hover:bg-white/5"><div><p className="break-all text-sm">{upload.filename}</p><p className="mt-1 text-xs text-zinc-500">{upload.total_records} records · {date(upload.created_at)}</p></div><Badge>{upload.status}</Badge></Link>)}</div> : <Empty>No uploads yet. Upload a CSV to start an investigation.</Empty>)}</>}</section></>;
}
