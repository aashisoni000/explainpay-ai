"use client";
import { useParams } from "next/navigation";
import { useCallback } from "react";
import { api } from "@/lib/api";
import { Badge, Contributions, date, Empty, ErrorNotice, JsonData, Loading, PageTitle, panelClass, percent, Stats, useResource } from "@/components/workspace/ui";
import { ReportActions } from "@/components/workspace/report-actions";

export default function WebsiteDetail() {
  const { id } = useParams<{ id: string }>();
  const load = useCallback(async () => {
    const scan = await api.website(id);
    return {
      ...scan,
      findings: scan.findings.map((finding) => ({
        ...finding,
        evidence: typeof finding.evidence === "string" ? finding.evidence : JSON.stringify(finding.evidence, null, 2),
      })),
    };
  }, [id]);
  const { data, error, loading, reload } = useResource(load);
  if (loading) return <Loading />;
  if (error) return <ErrorNotice error={error} retry={reload} />;
  if (!data) return null;
  return <><PageTitle eyebrow="Website investigation" title={data.normalized_domain} description={`Model ${data.model_version} · ${date(data.created_at)}`} /><p className="mb-6 break-all font-mono text-xs text-zinc-500">{data.url}</p><Stats items={[{ label: "ML phishing probability", value: percent(data.ml_probability) }, { label: "Risk level", value: <Badge>{data.risk_level}</Badge> }, { label: "Decision threshold", value: percent(data.threshold) }, { label: "Scan status", value: data.scan_status }]} /><div className={`${panelClass} mb-6`}><h2 className="text-lg">ML prediction: {data.ml_prediction === 1 ? "Phishing" : "Legitimate"}</h2><p className="mt-3 text-sm leading-6 text-zinc-400">This is a probabilistic URL-based assessment, not a guarantee of safety or proof of malicious activity. Threat-provider coverage depends on configuration and availability. A provider with no findings, unavailable access, or an incomplete scan must not be interpreted as a clean verdict. External URLs are displayed as text to avoid accidental visits.</p></div><Contributions values={data.explanation} /><section className="mt-8"><h2 className="mb-4 text-lg font-medium">Evidence & findings</h2>{data.findings.length ? <div className="space-y-3">{data.findings.map((finding, index) => <article key={index} className={panelClass}><div className="flex flex-wrap items-center gap-3"><h3 className="text-sm font-medium">{finding.finding_type}</h3><Badge>{finding.severity}</Badge><span className="text-xs text-zinc-500">{finding.source}</span></div><p className="mt-3 text-sm text-zinc-300">{finding.description}</p><p className="mt-3 break-all font-mono text-xs text-zinc-500">{finding.evidence}</p></article>)}</div> : <Empty>No findings were returned. Absence of findings does not establish safety.</Empty>}</section><section className="mt-8"><h2 className="mb-4 text-lg font-medium">Threat intelligence providers</h2>{data.providers.length ? <div className="space-y-3">{data.providers.map((provider, index) => <details key={`${provider.name}-${index}`} className={panelClass}><summary className="cursor-pointer text-sm">{provider.name} <span className="ml-3 text-zinc-500">{provider.status}</span></summary><div className="mt-4"><JsonData data={provider.details} /></div></details>)}</div> : <Empty>No provider results returned. Provider intelligence is unavailable for this scan.</Empty>}</section><details className={`${panelClass} mt-8`}><summary className="cursor-pointer text-sm">Extracted model features</summary><div className="mt-4"><JsonData data={data.features} /></div></details>{data.investigation_id && <ReportActions investigationId={data.investigation_id} />}</>;
}
