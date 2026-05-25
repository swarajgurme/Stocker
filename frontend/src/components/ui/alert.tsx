import type { ReactNode } from "react";
import { AlertCircle, CheckCircle2, Info } from "lucide-react";
import { cn } from "@/lib/utils";

const variants = {
  error: {
    box: "border-[var(--danger)]/25 bg-[var(--danger)]/8 text-[var(--danger)]",
    icon: AlertCircle,
  },
  success: {
    box: "border-[var(--success)]/25 bg-[var(--success)]/8 text-[var(--success)]",
    icon: CheckCircle2,
  },
  info: {
    box: "border-[var(--accent)]/25 bg-[var(--accent)]/8 text-[var(--accent)]",
    icon: Info,
  },
} as const;

export function Alert({
  variant = "info",
  title,
  children,
  className,
}: {
  variant?: keyof typeof variants;
  title?: string;
  children: ReactNode;
  className?: string;
}) {
  const v = variants[variant];
  const Icon = v.icon;
  return (
    <div
      role="alert"
      className={cn(
        "flex gap-3 rounded-[var(--radius)] border px-4 py-3 text-sm animate-fade-up",
        v.box,
        className,
      )}
    >
      <Icon className="mt-0.5 h-4 w-4 shrink-0 opacity-90" />
      <div>
        {title ? <p className="font-semibold">{title}</p> : null}
        <div className={title ? "mt-0.5 opacity-90" : ""}>{children}</div>
      </div>
    </div>
  );
}
