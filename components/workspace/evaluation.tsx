import type { Evaluation, ModelMetrics } from "@/types/api";
import { cellClass, date, JsonData, panelClass, percent, Stats } from "./ui";

function EvaluationTable({ label, data, positiveLabel }: { label: string; data: Evaluation; positiveLabel: string }) {
  const entries = [
    ["Precision", data.precision],
    ["Recall", data.recall],
    ["F1", data.f1],
    ["PR AUC", data.pr_auc],
    ["ROC AUC", data.roc_auc],
    ["False-positive rate", data.false_positive_rate],
    [`${positiveLabel} detection rate`, data.fraud_detection_rate],
    ["Decision threshold", data.threshold],
  ] as const;
  return <section className={panelClass}><h3 className="mb-4 text-sm font-medium">{label}</h3><dl className="space-y-3">{entries.map(([name, value]) => <div key={name} className="flex justify-between gap-4 text-xs"><dt className="text-zinc-500">{name}</dt><dd className="font-mono">{percent(value)}</dd></div>)}</dl><h4 className="mt-6 mb-3 text-xs text-zinc-400">Confusion matrix · actual rows / predicted columns</h4><div className="overflow-x-auto"><table className="w-full"><caption className="sr-only">{label} confusion matrix</caption><thead><tr><th className={cellClass} scope="col">Actual / predicted</th><th className={cellClass} scope="col">Legitimate</th><th className={cellClass} scope="col">{positiveLabel}</th></tr></thead><tbody>{data.confusion_matrix.map((row, index) => <tr key={index}><th className={cellClass} scope="row">{index === 0 ? "Legitimate" : positiveLabel}</th>{row.map((count, column) => <td className={cellClass} key={column}>{count.toLocaleString()}</td>)}</tr>)}</tbody></table></div></section>;
}

export function ModelEvaluation({ data, positiveLabel = "Fraud" }: { data: ModelMetrics; positiveLabel?: string }) {
  return <><Stats items={[{ label: "Selected model", value: data.selected_model }, { label: "Threshold", value: percent(data.threshold) }, { label: "Explanation units", value: data.explanation_units }, { label: "Split seed", value: data.split.seed }]} /><p className="mb-5 text-xs leading-6 text-zinc-500">Evaluated {date(data.created_at)} · Train {data.split.train} / validation {data.split.validation} / test {data.split.test}. Class weighting: {data.scale_pos_weight.toFixed(4)}.</p><div className="grid gap-4 xl:grid-cols-2"><EvaluationTable positiveLabel={positiveLabel} label="Selected model · held-out test" data={data.test} />{Object.entries(data.validation).map(([name, evaluation]) => <EvaluationTable positiveLabel={positiveLabel} key={name} label={`${name} · validation`} data={evaluation} />)}{Object.entries(data.test_comparison).map(([name, evaluation]) => <EvaluationTable positiveLabel={positiveLabel} key={`test-${name}`} label={`${name} · test comparison`} data={evaluation} />)}</div><section className={`${panelClass} mt-5`}><h3 className="text-sm font-medium">Evaluation limitations</h3>{data.limitations.length ? <ul className="mt-4 list-disc space-y-3 pl-5 text-sm leading-6 text-zinc-400">{data.limitations.map((limitation, index) => <li key={index}>{limitation}</li>)}</ul> : <p className="mt-3 text-sm text-zinc-500">No limitations were supplied by the evaluation service. Results still depend on the evaluation dataset.</p>}</section><details className={`${panelClass} mt-5`}><summary className="cursor-pointer text-sm">Threshold selection, dataset provenance & full metrics</summary><p className="mt-4 mb-4 break-all font-mono text-xs text-zinc-500">Dataset SHA-256: {data.dataset_sha256}</p><JsonData data={data} /></details></>;
}
