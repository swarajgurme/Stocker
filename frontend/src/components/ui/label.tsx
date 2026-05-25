import type { LabelHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Label({
  className,
  children,
  ...props
}: LabelHTMLAttributes<HTMLLabelElement>) {
  return (
    <label
      className={cn("flex flex-col gap-1.5 text-xs font-medium text-[var(--muted)]", className)}
      {...props}
    >
      {children}
    </label>
  );
}
