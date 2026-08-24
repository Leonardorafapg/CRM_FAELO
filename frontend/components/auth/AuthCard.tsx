import { ReactNode } from "react";

type AuthCardProps = {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer: ReactNode;
};

/** Card branco centralizado usado como moldura das telas de login/register. */
export function AuthCard({ title, subtitle, children, footer }: AuthCardProps) {
  return (
    <main className="flex flex-1 items-center justify-center px-4 py-10">
      <div className="w-full max-w-sm rounded-2xl border border-border-light bg-card-bg p-8 shadow-sm">
        <h1 className="font-heading text-2xl font-bold text-text-dark">
          {title}
        </h1>
        <p className="mt-1 text-sm text-text-muted">{subtitle}</p>

        {children}

        <p className="mt-6 text-center text-sm text-text-muted">{footer}</p>
      </div>
    </main>
  );
}
