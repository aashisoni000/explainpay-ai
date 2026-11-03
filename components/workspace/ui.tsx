"use client";

import { useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import type { Contribution } from "@/types/api";

export const buttonClass = "inline-flex min-h-10 items-center justify-center gap-2 rounded-md border border-white/20 px-4 py-2 text-sm font-medium transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-white";
export const inputClass = "min-h-11 w-full rounded-md border border-white/20 bg-black px-3 py-2 text-sm placeholder:text-zinc-600 focus:border-white focus:outline-none";
export const panelClass = "rounded-lg border border-white/15 bg-zinc-950/60 p-5 sm:p-6";
export const cellClass = "whitespace-nowrap border-b border-white/10 px-4 py-3 text-left text-sm";

export function message(error: unknown): string {
  return error instanceof ApiError ? `${error.status ? `API ${error.status}: ` : ""}${error.message}` : error instanceof Error ? error.message : "Something went wrong. Please try again.";
}

export function useResource<T>(loader: () => Promise<T>) {
  const [revision, setRevision] = useState(0);
  const [result, setResult] = useState<{ loader: () => Promise<T>; revision: number; data: T | null; error: string | null } | null>(null);
  useEffect(() => {
    let active = true;
    loader().then((data) => { if (active) setResult({ loader, revision, data, error: null }); })
      .catch((cause: unknown) => { if (active) setResult({ loader, revision, data: null, error: message(cause) }); });
    return () => { active = false; };
  }, [loader, revision]);
  const loading = result?.loader !== loader || result?.revision !== revision;
  function reload() { setRevision((value) => value + 1); }
  return { data: loading ? null : result?.data ?? null, error: loading ? null : result?.error ?? null, loading, reload };
}

export function PageTitle({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return <header className="mb-9"><p className="mb-3 text-xs tracking-[0.2em] text-zinc-500 uppercase">{eyebrow}</p><h1 className="text-3xl font-medium tracking-tight sm:text-4xl">{title}</h1><p className="mt-3 max-w-2xl text-sm leading-6 text-zinc-400">{description}</p></header>;
}

export function ErrorNotice({ error, retry }: { error: string | null; retry?: () => void }) {
  if (!error) return null;
  return <div role="alert" className="my-4 rounded-md border border-red-400/30 bg-red-400/5 p-4 text-sm text-red-200"><p>{error}</p>{retry && <button className={`${buttonClass} mt-3`} onClick={retry}>Try again</button>}</div>;
}

export function Loading() { return <p role="status" className="p-6 text-sm text-zinc-400">Loading live data…</p>; }
export function Empty({ children }: { children: React.ReactNode }) { return <p className="rounded-lg border border-dashed border-white/20 p-8 text-center text-sm text-zinc-500">{children}</p>; }
export function Badge({ children }: { children: React.ReactNode }) { return <span className="inline-flex rounded border border-white/20 px-2 py-1 text-xs text-zinc-300">{children}</span>; }
export function percent(value: number) { return `${(value * 100).toFixed(1)}%`; }
export function date(value: string) { return new Date(value).toLocaleString(); }
export function JsonData({ data }: { data: unknown }) { return <pre className="max-h-96 overflow-auto rounded-md border border-white/10 bg-black p-4 text-xs leading-6 text-zinc-300">{JSON.stringify(data, null, 2)}</pre>; }
export function Stats({ items }: { items: { label: string; value: React.ReactNode }[] }) {
  return <dl className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">{items.map((item) => <div key={item.label} className={panelClass}><dt className="text-xs text-zinc-500">{item.label}</dt><dd className="mt-3 break-words text-xl font-medium">{item.value}</dd></div>)}</dl>;
}

export function Contributions({ values }: { values: Contribution[] }) {
  const max = Math.max(...values.map((item) => Math.abs(item.contribution)), 0.000001);
  if (!values.length) return <Empty>No feature explanations were returned by the model.</Empty>;
  return <div className={panelClass}><h2 className="text-lg font-medium">Feature contributions</h2><p className="mt-2 mb-6 text-sm text-zinc-400">SHAP contributions are log-odds, not probability points: positive values increase the model output; negative values decrease it. Their sum plus the base value equals predicted log-odds. These explain the prediction, not causation.</p><div className="space-y-5">{[...values].sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution)).map((item) => <div key={item.feature}><div className="mb-2 flex flex-wrap justify-between gap-2 text-xs"><span className="font-mono">{item.feature} <span className="text-zinc-500">(value: {item.value.toFixed(4)})</span></span><span className={item.contribution >= 0 ? "text-amber-300" : "text-sky-300"}>{item.contribution >= 0 ? "+" : ""}{item.contribution.toFixed(5)} · {item.contribution >= 0 ? "increases" : "decreases"}</span></div><div aria-hidden="true" className="relative flex h-3 overflow-hidden rounded bg-white/5"><div className="relative w-1/2 border-r border-white/30">{item.contribution < 0 && <div className="absolute right-0 h-full bg-sky-300/80" style={{ width: `${Math.abs(item.contribution) / max * 100}%` }} />}</div><div className="relative w-1/2">{item.contribution >= 0 && <div className="h-full bg-amber-300/80" style={{ width: `${item.contribution / max * 100}%` }} />}</div></div></div>)}</div></div>;
}
