import Link from "next/link";
import { IconChevronLeft } from "@/components/layout/icons";

/** Botão de "voltar" usado no topo das telas internas do dashboard. */
export function BackLink({ href, children }: { href: string; children: string }) {
  return (
    <Link
      href={href}
      className="inline-flex items-center gap-1.5 rounded-lg border border-border-light bg-card-bg px-3 py-1.5 text-sm text-text-dark transition-colors hover:bg-page-bg"
    >
      <IconChevronLeft width={14} height={14} />
      {children}
    </Link>
  );
}
