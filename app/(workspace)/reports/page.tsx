"use client";
import { useState } from "react";
import Link from "next/link";
import { api, downloadReport } from "@/lib/api";
import { buttonClass, cellClass, date, Empty, ErrorNotice, inputClass, Loading, message, PageTitle, panelClass, useResource } from "@/components/workspace/ui";

export default function Reports() {
  const reports = useResource(api.reports);
  const investigations = useResource(api.investigations);
  const [selected, setSelected] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  async function generate(event: React.FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setBusy("generate"); setError(null); setNotice(null);
    try { await api.generateReport(selected); reports.reload(); setNotice("Report generated and saved. Download it from the list below."); }
    catch (cause) { setError(message(cause)); }
    finally { setBusy(null); }
  }
  async function download(id: string) {
    setBusy(id); setError(null);
    try { await downloadReport(id); }
    catch (cause) { setError(message(cause)); }
    finally { setBusy(null); }
  }
  return <><PageTitle eyebrow="Evidence exports" title="Make the findings portable." description="Generate PDF reports from saved investigations. Downloads contain the evidence available at generation time, not a guarantee of safety." /><form onSubmit={generate} className={`${panelClass} mb-8`}><label htmlFor="report-investigation" className="text-sm">Generate an investigation report</label><div className="mt-4 flex flex-col gap-3 sm:flex-row"><select id="report-investigation" className={inputClass} value={selected} onChange={(event) => setSelected(event.target.value)} disabled={investigations.loading || Boolean(investigations.error) || Boolean(busy)}><option value="">Select a saved investigation</option>{investigations.data?.map((item) => <option key={item.id} value={item.id}>{item.title} · {item.id}</option>)}</select><button className={`${buttonClass} shrink-0`} disabled={!selected || Boolean(busy) || Boolean(investigations.error)}>{busy === "generate" ? "Generating…" : "Generate PDF"}</button></div>{investigations.loading && <Loading />}<ErrorNotice error={investigations.error} retry={investigations.reload} />{investigations.data?.length === 0 && <p className="mt-4 text-sm text-zinc-500">No saved investigations. Analyze transactions or scan a website first.</p>}</form><ErrorNotice error={error} />{notice && <p role="status" className="mb-4 text-sm text-zinc-300">{notice}</p>}<div className="mb-4 flex items-center justify-between"><h2 className="text-lg">Saved reports</h2><button className={buttonClass} disabled={reports.loading} onClick={reports.reload}>Refresh</button></div>{reports.loading ? <Loading /> : <><ErrorNotice error={reports.error} retry={reports.reload} />{reports.data && (reports.data.length ? <div className="overflow-x-auto rounded-lg border border-white/15"><table className="w-full"><caption className="sr-only">Saved investigation reports</caption><thead><tr>{["Report", "Investigation", "Generated", "Download"].map((label) => <th className={cellClass} scope="col" key={label}>{label}</th>)}</tr></thead><tbody>{reports.data.map((report) => <tr key={report.id}><td className={cellClass}><p>{report.report_type}</p><p className="mt-1 font-mono text-xs text-zinc-600">{report.id}</p></td><td className={cellClass}><Link className="underline underline-offset-4" href={`/investigations/${encodeURIComponent(report.investigation_id)}`}>{report.investigation_id}</Link></td><td className={cellClass}>{date(report.created_at)}</td><td className={cellClass}><button className={buttonClass} disabled={Boolean(busy)} onClick={() => download(report.id)}>{busy === report.id ? "Downloading…" : "Download PDF"}<span className="sr-only"> {report.id}</span></button></td></tr>)}</tbody></table></div> : <Empty>No reports yet. Select an investigation above to generate your first PDF.</Empty>)}</>}</>;
}
