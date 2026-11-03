"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback } from "react";
import { api } from "@/lib/api";
import { validWebsite } from "@/lib/workspace";
import { Badge, buttonClass, Contributions, date, ErrorNotice, Loading, PageTitle, panelClass, percent, Stats, useResource } from "@/components/workspace/ui";
import { ReportActions } from "@/components/workspace/report-actions";

export default function TransactionDetail() {
  const { id } = useParams<{ id: string }>();
  const load = useCallback(() => api.transaction(id), [id]);
  const { data, error, loading, reload } = useResource(load);
  if (loading) return <Loading />;
  if (error) return <ErrorNotice error={error} retry={reload} />;
  if (!data) return null;
  return <><PageTitle eyebrow="Transaction explanation" title={data.transaction_reference || data.id} description={`Model ${data.model_version} · ${date(data.created_at)}`} /><Stats items={[{ label: "Fraud probability", value: percent(data.fraud_probability) }, { label: "Decision threshold", value: percent(data.threshold) }, { label: "Risk level", value: <Badge>{data.risk_level}</Badge> }, { label: "Amount (currency unspecified)", value: data.amount.toLocaleString(undefined, { minimumFractionDigits: 2 }) }]} /><div className={`${panelClass} mb-6`}><h2 className="text-lg">Prediction: {data.prediction === 1 ? "Flagged" : "Legitimate"}</h2><p className="mt-2 text-sm text-zinc-400">Base value (log-odds): {data.base_value.toFixed(5)} · Anomaly score: {data.anomaly_score === null ? "Unavailable" : data.anomaly_score.toFixed(5)} · Anomaly: {data.is_anomaly === null ? "Unavailable" : data.is_anomaly ? "Yes" : "No"}</p><p className="mt-4 border-l-2 border-amber-300/60 pl-3 text-sm leading-6 text-zinc-400">Anonymized PCA features (such as V1–V28) cannot be interpreted as real-world transaction attributes. Contributions describe model behavior, not proof of fraud. SHAP contributions are log-odds, not probability points: their sum plus the base value equals the predicted log-odds.</p></div><Contributions values={data.explanation} /><div className="mt-6 flex flex-wrap gap-3">{data.upload_id && <Link className={buttonClass} href={`/transactions?upload=${encodeURIComponent(data.upload_id)}`}>View source upload</Link>}{data.merchant_url && validWebsite(data.merchant_url) && <Link className={buttonClass} href={`/website-scanner?url=${encodeURIComponent(data.merchant_url)}`}>Investigate merchant website</Link>}</div>{data.investigation_id && <ReportActions investigationId={data.investigation_id} />}</>;
}
