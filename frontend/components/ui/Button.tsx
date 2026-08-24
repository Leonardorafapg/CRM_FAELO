import { ButtonHTMLAttributes } from "react";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  loading?: boolean;
  loadingText?: string;
};

/** Botão primário (azul sólido) usado nos formulários de auth. */
export function Button({
  loading,
  loadingText,
  disabled,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      disabled={disabled || loading}
      className="mt-2 rounded-lg bg-accent-blue py-2 font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-60"
      {...props}
    >
      {loading ? loadingText ?? "Carregando..." : children}
    </button>
  );
}
