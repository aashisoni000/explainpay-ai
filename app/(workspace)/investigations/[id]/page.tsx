"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback } from "react";
import { api } from "@/lib/api";
import { investigationHref } from "@/lib/workspace";
import { Badge, buttonClass, date, ErrorNotice, JsonData, Loading, PageTitle, panelClass, useResource } from "@/components/workspace/ui";
import { ReportActions } from "@/components/workspace/report-actions";

export default function InvestigationDetail() {
  const { id } = useParams<{ id: string }>();
  const load = useCallback(() => api.investigation(id), [id]);
  const { data, error, loading, reload } = useResource(load);
  if (loading) return <Loading />;
  if (error) return <ErrorNotice error={error} retry={reload} />;
  if (!data) return null;
  const href = investigationHref(data);
  return <><PageTitle eyebrow={data.investigation_type} title={data.title} description={`Created ${date(data.created_at)} · Updated ${date(data.updated_at)}`} /><div className={panelClass}><div className="flex gap-3"><Badge>{data.status}</Badge>{data.risk_level && <Badge>{data.risk_level}</Badge>}</div><p className="mt-4 break-all font-mono text-xs text-zinc-500">Investigation {data.id}</p>{href ? <Link className={`${buttonClass} mt-5`} href={href}>Open source evidence</Link> : <p className="mt-5 text-sm text-zinc-500">No source resource is linked to this investigation.</p>}</div>{(data.upload || data.transaction || data.website) && <details className={`${panelClass} mt-6`}><summary className="cursor-pointer text-sm">Saved investigation evidence</summary><div className="mt-4"><JsonData data={data.upload ?? data.transaction ?? data.website} /></div></details>}<ReportActions investigationId={data.id} /></>;
}
