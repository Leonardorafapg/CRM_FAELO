import { InputHTMLAttributes } from "react";

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
};

/** Input com label acima, no padrão visual usado em todos os formulários de auth. */
export function Input({ label, id, className, ...props }: InputProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm text-text-muted">
        {label}
      </label>
      <input
        id={id}
        className={`rounded-lg border border-border-light bg-page-bg px-3 py-2 text-text-dark outline-none focus:border-accent-blue ${className ?? ""}`}
        {...props}
      />
    </div>
  );
}
