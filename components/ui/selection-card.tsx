import Link from "next/link";
import { ArrowUpRight, CreditCard, Globe } from "lucide-react";

type SelectionCardProps = {
  title: string;
  description: string;
  cta: string;
  href: string;
  icon: "credit-card" | "globe";
};

export function SelectionCard({
  title,
  description,
  cta,
  href,
  icon,
}: SelectionCardProps) {
  const Icon = icon === "credit-card" ? CreditCard : Globe;

  return (
    <Link
      href={href}
      className="group flex h-full flex-col border border-white/15 bg-black/80 p-6 text-left transition-colors duration-300 hover:border-white/45 hover:bg-neutral-950/90 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-white sm:p-8"
    >
      <Icon
        aria-hidden="true"
        className="mb-8 size-7 text-white/75 transition-colors group-hover:text-white group-focus-visible:text-white"
        strokeWidth={1.25}
      />
      <h3 className="text-xl font-medium tracking-tight text-white">{title}</h3>
      <p className="mt-3 max-w-xs flex-1 text-sm leading-6 text-neutral-400">
        {description}
      </p>
      <span className="mt-8 flex items-center justify-between gap-4 text-sm font-medium text-neutral-200">
        {cta}
        <ArrowUpRight
          aria-hidden="true"
          className="size-4 text-neutral-500 transition duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-white group-focus-visible:translate-x-0.5 group-focus-visible:-translate-y-0.5 group-focus-visible:text-white motion-reduce:transform-none motion-reduce:transition-none"
          strokeWidth={1.5}
        />
      </span>
    </Link>
  );
}
