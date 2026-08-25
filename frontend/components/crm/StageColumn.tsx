import { ReactNode } from "react";

type StageColumnProps = {
  title: string;
  count: number;
  children: ReactNode;
};

export function StageColumn({ title, count, children }: StageColumnProps) {
  return (
    <div className="flex w-72 shrink-0 flex-col gap-3 rounded-xl border border-border-light bg-page-bg p-3">
      <div className="flex items-center justify-between">
        <h2 className="font-medium text-text-dark">{title}</h2>
        <span className="text-xs text-text-muted">{count}</span>
      </div>
      <div className="flex flex-col gap-2">{children}</div>
    </div>
  );
}
