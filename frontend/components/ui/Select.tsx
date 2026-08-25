import { SelectHTMLAttributes } from "react";

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label?: string;
};

/** Select no mesmo padrão visual do Input — com ou sem label acima. */
export function Select({ label, id, className, children, ...props }: SelectProps) {
  const select = (
    <select
      id={id}
      className={`rounded-lg border border-border-light bg-page-bg px-3 py-2 text-sm text-text-dark outline-none focus:border-accent-blue ${className ?? ""}`}
      {...props}
    >
      {children}
    </select>
  );

  if (!label) return select;

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm text-text-muted">
        {label}
      </label>
      {select}
    </div>
  );
}
