import type { ButtonHTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const btn = cva(
  "inline-flex items-center justify-center gap-2 rounded-[var(--radius)] text-sm font-medium transition-all duration-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:pointer-events-none disabled:opacity-45 active:scale-[0.98]",
  {
    variants: {
      variant: {
        primary:
          "bg-[var(--accent)] text-[var(--accent-foreground)] shadow-md hover:brightness-110 hover:shadow-[var(--shadow-glow)]",
        ghost:
          "bg-transparent text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text)]",
        outline:
          "border border-[var(--border-strong)] bg-[var(--surface2)] text-[var(--text)] hover:border-[var(--accent)]/40 hover:bg-[var(--surface-hover)]",
        danger:
          "border border-[var(--danger)]/30 bg-[var(--danger)]/10 text-[var(--danger)] hover:bg-[var(--danger)]/15",
        secondary:
          "bg-[var(--surface2)] text-[var(--text)] border border-[var(--border)] hover:bg-[var(--surface-hover)]",
      },
      size: {
        sm: "h-8 px-3 text-xs",
        md: "h-10 px-4",
        lg: "h-11 px-5",
        icon: "h-9 w-9 p-0",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof btn>;

export function Button({ className, variant, size, ...props }: ButtonProps) {
  return (
    <button className={cn(btn({ variant, size }), className)} {...props} />
  );
}
