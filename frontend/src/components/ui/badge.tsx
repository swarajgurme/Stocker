import type { HTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badge = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
  {
    variants: {
      tone: {
        default:
          "border-[var(--accent)]/25 bg-[var(--accent)]/10 text-[var(--accent)]",
        muted: "border-[var(--border)] bg-[var(--surface2)] text-[var(--muted)]",
        healthy:
          "border-[var(--success)]/30 bg-[var(--success)]/10 text-[var(--success)]",
        warning:
          "border-[var(--warn)]/30 bg-[var(--warn)]/10 text-[var(--warn)]",
        critical:
          "border-[var(--danger)]/30 bg-[var(--danger)]/10 text-[var(--danger)]",
        high: "border-orange-500/30 bg-orange-500/10 text-orange-400",
        medium: "border-amber-500/30 bg-amber-500/10 text-amber-400",
        low: "border-slate-500/30 bg-slate-500/10 text-slate-400",
      },
    },
    defaultVariants: { tone: "default" },
  },
);

export type BadgeProps = HTMLAttributes<HTMLSpanElement> &
  VariantProps<typeof badge>;

export function Badge({ className, tone, ...props }: BadgeProps) {
  return <span className={cn(badge({ tone }), className)} {...props} />;
}
