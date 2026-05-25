import type { InputHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-10 w-full rounded-[var(--radius)] border border-[var(--border-strong)] bg-[var(--bg-elevated)] px-3 text-sm text-[var(--text)] shadow-sm transition placeholder:text-[var(--muted)]",
        "hover:border-[var(--accent)]/30 focus:border-[var(--accent)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/20",
        className,
      )}
      {...props}
    />
  );
}
