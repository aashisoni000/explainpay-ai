"use client";

import { api, API_URL } from "@/lib/api";
import { Badge, buttonClass, ErrorNotice, Loading, PageTitle, panelClass, useResource } from "@/components/workspace/ui";
import { ModelEvaluation } from "@/components/workspace/evaluation";

export default function Settings() {
  const health = useResource(api.health);
  const system = useResource(api.status);
  const metrics = useResource(api.metrics);
  const websiteMetrics = useResource(api.websiteMetrics);

  return (
    <>
      <PageTitle eyebrow="System & models" title="Know what is running." description="Live service availability, model readiness, provider configuration, and evaluation metrics. This view is read-only; it does not simulate configuration changes." />
      <div className={`${panelClass} mb-6`}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg">API connection</h2>
          <button className={buttonClass} disabled={health.loading || system.loading || metrics.loading || websiteMetrics.loading} onClick={() => { health.reload(); system.reload(); metrics.reload(); websiteMetrics.reload(); }}>Refresh all</button>
        </div>
        <p className="mt-3 break-all font-mono text-xs text-zinc-500">{API_URL}</p>
        <p className="mt-2 text-xs text-zinc-600">Configured via NEXT_PUBLIC_API_URL at frontend build time.</p>
        {health.loading ? <Loading /> : <><ErrorNotice error={health.error} retry={health.reload} />{health.data && <p className="mt-4 text-sm">Health: <Badge>{health.data.status}</Badge></p>}</>}
      </div>
      {system.loading ? <Loading /> : (
        <>
          <ErrorNotice error={system.error} retry={system.reload} />
          {system.data && <>
            <div className="grid gap-4 md:grid-cols-3">
              {[{ name: "Database", state: system.data.database }, { name: "Fraud model", state: system.data.models.fraud }, { name: "Phishing model", state: system.data.models.phishing }].map(({ name, state }) => (
                <section key={name} className={panelClass}>
                  <h2 className="mb-4 text-sm">{name}</h2>
                  <Badge>{state.available ? "Available" : "Unavailable"}</Badge>
                  {state.error && <p className="mt-4 break-words text-xs leading-5 text-red-200">{state.error}</p>}
                </section>
              ))}
            </div>
            <section className={`${panelClass} mt-6`}>
              <h2 className="mb-5 text-lg">External providers</h2>
              <dl className="divide-y divide-white/10">
                {Object.entries(system.data.providers).map(([name, status]) => <div key={name} className="flex flex-wrap justify-between gap-3 py-4 text-sm"><dt className="font-mono text-xs text-zinc-400">{name}</dt><dd><Badge>{status}</Badge></dd></div>)}
              </dl>
              <p className="mt-4 text-xs leading-5 text-zinc-500">Keys and provider configuration are managed on the API server. Unconfigured or unavailable providers cannot contribute live threat intelligence.</p>
            </section>
          </>}
        </>
      )}
      <section className={`${panelClass} mt-6`}>
        <h2 className="mb-3 text-lg">Model evaluation & runtime metrics</h2>
        <p className="mb-5 text-sm leading-6 text-zinc-500">Fraud model evaluation returned directly by the evaluation service, including dataset context and limitations. Missing metrics are not replaced with sample values.</p>
        {metrics.loading ? <Loading /> : <><ErrorNotice error={metrics.error} retry={metrics.reload} />{metrics.data && <ModelEvaluation data={metrics.data} />}</>}
      </section>
      <section className={`${panelClass} mt-6`}>
        <h2 className="mb-3 text-lg">Website phishing model evaluation</h2>
        <p className="mb-5 text-sm leading-6 text-zinc-500">The phishing dataset is highly imbalanced toward malicious URLs. Review the benign false-positive rate, not just phishing F1 or PR AUC. Unsupported URLs were excluded; these results do not establish website safety.</p>
        {websiteMetrics.loading ? <Loading /> : <><ErrorNotice error={websiteMetrics.error} retry={websiteMetrics.reload} />{websiteMetrics.data && <ModelEvaluation data={websiteMetrics.data} positiveLabel="Phishing" />}</>}
      </section>
    </>
  );
}
