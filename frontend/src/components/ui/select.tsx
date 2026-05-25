import type { SelectHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Select({
  className,
  children,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "h-10 w-full cursor-pointer appearance-none rounded-[var(--radius)] border border-[var(--border-strong)] bg-[var(--bg-elevated)] px-3 pr-8 text-sm text-[var(--text)] transition",
        "hover:border-[var(--accent)]/30 focus:border-[var(--accent)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/20",
        className,
      )}
      {...props}
    >
      {children}
    </select>
  );
}
