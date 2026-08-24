export function ErrorMessage({ children }: { children: string | null }) {
  if (!children) return null;
  return <p className="text-sm text-red-600">{children}</p>;
}
