import { SelectionCard } from "@/components/ui/selection-card";
import { WebGLShader } from "@/components/ui/web-gl-shader";

export default function Home() {
  return (
    <>
      <WebGLShader />
      <div className="relative isolate mx-auto flex min-h-svh w-full max-w-6xl flex-col px-5 sm:px-10">
        <header className="flex flex-col items-center pt-10 sm:pt-14">
          <span className="text-2xl font-medium tracking-[-0.06em] text-white">
            ExplainPay<span aria-hidden="true" className="ml-1 text-neutral-500">.</span>
          </span>
          <p className="mt-3 text-[9px] font-medium tracking-[0.3em] text-neutral-400 sm:text-[10px]">
            FINANCIAL TRUST INTELLIGENCE
          </p>
        </header>

        <main className="flex flex-1 flex-col items-center justify-center py-16 sm:py-20">
          <div className="hero-copy text-center">
            <h1 className="text-[clamp(2.5rem,5.4vw,4.5rem)] leading-[1.08] font-normal tracking-[-0.055em] text-white">
              Know the risk.
              <br />
              <span className="text-neutral-300">Understand the reason.</span>
            </h1>
            <p className="mx-auto mt-6 max-w-sm text-sm leading-6 text-neutral-400 sm:max-w-none sm:text-base">
              Your financial safety starts with knowing what to trust.
            </p>
          </div>

          <section
            aria-labelledby="selection-heading"
            className="mt-12 w-full max-w-3xl border border-white/20 bg-black/60 p-4 sm:mt-14 sm:p-6"
          >
            <div className="mb-5 flex items-center gap-3 sm:mb-6">
              <span aria-hidden="true" className="size-1 bg-neutral-400" />
              <h2 id="selection-heading" className="text-xs font-normal tracking-wide text-neutral-300">
                What are you here for today?
              </h2>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <SelectionCard
                title="Detect Financial Fraud"
                description="Investigate transactions and understand suspicious financial activity through explainable AI."
                icon="credit-card"
                cta="Analyse Transactions"
                href="/transactions"
              />
              <SelectionCard
                title="Check Website Trust"
                description="Investigate websites for phishing, suspicious domains and potential online scams."
                icon="globe"
                cta="Scan a Website"
                href="/website-scanner"
              />
            </div>
          </section>
        </main>
      </div>
    </>
  );
}
