import type { LucideIcon } from "lucide-react";
import { motion } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function StatCard({
  label,
  value,
  hint,
  icon: Icon,
  trend,
  className,
  delay = 0,
}: {
  label: string;
  value: string;
  hint?: string;
  icon?: LucideIcon;
  trend?: "up" | "down" | "neutral";
  className?: string;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.35 }}
    >
      <Card className={cn("overflow-hidden", className)}>
        <CardContent className="relative p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-[var(--muted)]">
                {label}
              </p>
              <p className="mt-2 text-2xl font-semibold tabular-nums tracking-tight text-[var(--text)]">
                {value}
              </p>
              {hint ? (
                <p className="mt-1.5 text-xs text-[var(--muted)]">{hint}</p>
              ) : null}
            </div>
            {Icon ? (
              <div className="flex h-10 w-10 items-center justify-center rounded-[var(--radius)] bg-[var(--accent)]/10 text-[var(--accent)]">
                <Icon className="h-5 w-5" />
              </div>
            ) : null}
          </div>
          {trend ? (
            <div
              className={cn(
                "mt-3 inline-flex text-[10px] font-medium uppercase tracking-wide",
                trend === "up" && "text-[var(--success)]",
                trend === "down" && "text-[var(--danger)]",
                trend === "neutral" && "text-[var(--muted)]",
              )}
            >
              {trend === "up" ? "↑ Improving" : trend === "down" ? "↓ Attention" : "— Stable"}
            </div>
          ) : null}
        </CardContent>
      </Card>
    </motion.div>
  );
}
