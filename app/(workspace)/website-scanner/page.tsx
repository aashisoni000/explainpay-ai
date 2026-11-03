"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { validWebsite } from "@/lib/workspace";
import { Badge, buttonClass, date, Empty, ErrorNotice, inputClass, Loading, message, PageTitle, panelClass, percent, useResource } from "@/components/workspace/ui";

function ScanForm({ initialUrl }: { initialUrl: string }) {
  const router = useRouter();
  const [url, setUrl] = useState(initialUrl);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const value = url.trim();
    if (!validWebsite(value)) { setError("Enter a complete HTTP or HTTPS URL without embedded credentials (for example https://example.com)."); return; }
    setBusy(true); setError(null);
    try { router.push(`/website-scanner/${encodeURIComponent((await api.scan(value)).id)}`); }
    catch (cause) { setError(message(cause)); }
    finally { setBusy(false); }
  }
  return <form className={`${panelClass} mb-9`} onSubmit={submit} noValidate><label htmlFor="website-url" className="text-sm font-medium">Website URL</label><p id="url-help" className="mt-2 mb-4 text-xs leading-5 text-zinc-500">The API analyzes URL features and queries available threat providers. Only submit URLs you are authorized to investigate.</p><div className="flex flex-col gap-3 sm:flex-row"><input id="website-url" type="url" required autoComplete="url" aria-describedby={error ? "url-help url-error" : "url-help"} aria-invalid={Boolean(error)} value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://example.com" className={inputClass} disabled={busy} /><button className={`${buttonClass} shrink-0 bg-white text-black hover:bg-zinc-200`} disabled={busy || !url.trim()}>{busy ? "Scanning website…" : "Analyze website"}</button></div><div id="url-error"><ErrorNotice error={error} /></div>{busy && <p role="status" className="mt-4 text-xs text-zinc-400">Waiting for the model and configured providers. This may take a moment.</p>}</form>;
}

export default function WebsiteScanner() {
  const query = useSearchParams();
  const initialUrl = query.get("url") ?? "";
  const history = useResource(api.scans);
  return <><PageTitle eyebrow="Website intelligence" title="Look beyond the URL." description="Investigate a website with machine learning, explainable URL features, and external threat intelligence where available." /><ScanForm key={initialUrl} initialUrl={initialUrl} /><div className="mb-5 flex items-center justify-between"><h2 className="text-lg font-medium">Scan history</h2><button className={buttonClass} onClick={history.reload} disabled={history.loading}>Refresh</button></div>{history.loading ? <Loading /> : <><ErrorNotice error={history.error} retry={history.reload} />{history.data && (history.data.length ? <div className="divide-y divide-white/10 rounded-lg border border-white/15">{history.data.map((scan) => <Link key={scan.id} href={`/website-scanner/${encodeURIComponent(scan.id)}`} className="flex flex-wrap items-center justify-between gap-4 p-5 hover:bg-white/5"><div className="min-w-0"><p className="break-all text-sm">{scan.normalized_domain || scan.url}</p><p className="mt-2 text-xs text-zinc-500">{date(scan.created_at)} · {scan.scan_status}</p></div><div className="flex items-center gap-4"><span className="text-sm text-zinc-400">{percent(scan.ml_probability)}</span><Badge>{scan.risk_level}</Badge></div></Link>)}</div> : <Empty>No scans yet. Submit a website URL to begin.</Empty>)}</>}</>;
}
