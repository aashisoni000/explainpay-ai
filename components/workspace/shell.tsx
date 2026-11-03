"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { ArrowUpRight, FileText, Globe, Menu, Search, Settings, X, Layers } from "lucide-react";

const navigation = [
  { href: "/transactions", label: "Transactions", icon: Layers },
  { href: "/website-scanner", label: "Website scanner", icon: Globe },
  { href: "/investigations", label: "Investigations", icon: Search },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/settings", label: "System & models", icon: Settings },
];

export function WorkspaceShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const current = navigation.find((item) => pathname.startsWith(item.href));
  const detail = pathname.split("/").filter(Boolean).length > 1;
  return <div className="min-h-screen bg-black text-zinc-100"><a className="sr-only z-50 bg-white p-3 text-black focus:not-sr-only focus:fixed" href="#workspace-main">Skip to content</a><header className="flex h-18 items-center justify-between border-b border-white/15 px-5 lg:px-8"><Link href="/" className="text-lg font-semibold tracking-tight">ExplainPay<span className="ml-2 text-xs font-normal text-zinc-500">/ intelligence</span></Link><Link href="/" className="hidden items-center gap-2 text-xs text-zinc-400 sm:flex">Back to overview <ArrowUpRight size={14} /></Link><button aria-label={open ? "Close navigation" : "Open navigation"} aria-expanded={open} aria-controls="workspace-nav" onClick={() => setOpen(!open)} className="rounded border border-white/20 p-2 lg:hidden">{open ? <X size={20} /> : <Menu size={20} />}</button></header><div className="lg:grid lg:grid-cols-[230px_minmax(0,1fr)]"><aside className={`${open ? "block" : "hidden"} border-b border-white/15 p-5 lg:block lg:min-h-[calc(100vh-72px)] lg:border-r lg:border-b-0`}><p className="mb-5 px-3 text-[10px] tracking-[0.2em] text-zinc-600 uppercase">Workspace</p><nav id="workspace-nav" aria-label="Workspace navigation" className="space-y-2">{navigation.map(({ href, label, icon: Icon }) => <Link key={href} href={href} onClick={() => setOpen(false)} aria-current={pathname.startsWith(href) ? "page" : undefined} className={`flex items-center gap-3 rounded-md border px-3 py-3 text-sm transition ${pathname.startsWith(href) ? "border-white/20 bg-white/7 text-white" : "border-transparent text-zinc-500 hover:bg-white/5 hover:text-white"}`}><Icon size={16} />{label}</Link>)}</nav><p className="mt-10 px-3 text-xs leading-5 text-zinc-600">Evidence, not certainty.<br />Always review model findings.</p></aside><div className="min-w-0"><nav aria-label="Breadcrumb" className="flex h-14 items-center gap-3 border-b border-white/10 px-5 text-xs text-zinc-500 sm:px-8"><Link href="/">ExplainPay</Link><span aria-hidden="true">/</span>{detail ? <><Link href={current?.href ?? "/investigations"}>{current?.label}</Link><span aria-hidden="true">/</span><span className="text-zinc-300">Detail</span></> : <span className="text-zinc-300">{current?.label}</span>}</nav><main id="workspace-main" className="mx-auto max-w-7xl px-5 py-9 sm:px-8 lg:py-12">{children}</main></div></div></div>;
}
