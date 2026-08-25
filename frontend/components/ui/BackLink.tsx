import Link from "next/link";

/** Link de "voltar" usado no topo das telas internas do dashboard. */
export function BackLink({ href, children }: { href: string; children: string }) {
  return (
    <Link href={href} className="text-sm text-accent-blue hover:underline">
      {children}
    </Link>
  );
}
