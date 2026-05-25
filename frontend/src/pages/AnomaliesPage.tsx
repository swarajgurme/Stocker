import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { motion } from "framer-motion";
import { Radar } from "lucide-react";
import { anomalyAPI, type AnomalyRow } from "@/services/api";
import { PageHeader } from "@/components/ui/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { ChartCard } from "@/components/ui/chart-card";
import { PageSkeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { CHART_AXIS, CHART_GRID, CHART_WARN, chartTooltipStyle } from "@/lib/chart-theme";

export default function AnomaliesPage() {
  const [rows, setRows] = useState<AnomalyRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const r = await anomalyAPI.list({ unreviewed_only: "false", limit: "80" });
      setRows(r.data.anomalies);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const chartData = Object.values(
    rows.reduce<Record<string, { severity: string; count: number }>>((acc, row) => {
      const key = row.severity ?? "unknown";
      acc[key] = acc[key] || { severity: key, count: 0 };
      acc[key].count += 1;
      return acc;
    }, {}),
  );

  const runDetect = async () => {
    setBusy(true);
    try {
      await anomalyAPI.detect({ lookback_days: 120 });
      await load();
    } finally {
      setBusy(false);
    }
  };

  const sevTone = (s?: string) => {
    switch (s) {
      case "critical":
        return "critical";
      case "high":
        return "high";
      case "medium":
        return "medium";
      default:
        return "low";
    }
  };

  return (
    <div className="mx-auto max-w-7xl space-y-8">
      <PageHeader
        title="Anomaly monitoring"
        description="Statistical surveillance on demand and inventory stress with severity classification."
        actions={
          <Button type="button" onClick={() => void runDetect()} disabled={busy}>
            {busy ? <Spinner className="h-5 w-5" /> : "Run detection"}
          </Button>
        }
      />

      <ChartCard title="Severity distribution" height="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="4 6" stroke={CHART_GRID} vertical={false} />
            <XAxis dataKey="severity" stroke={CHART_AXIS} tick={{ fontSize: 11 }} />
            <YAxis stroke={CHART_AXIS} />
            <Tooltip contentStyle={chartTooltipStyle()} />
            <Bar dataKey="count" fill={CHART_WARN} radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      {loading ? (
        <PageSkeleton />
      ) : rows.length === 0 ? (
        <EmptyState
          icon={Radar}
          title="No anomalies detected"
          description="Run the detection job to scan recent sales and inventory signals."
          action={
            <Button type="button" onClick={() => void runDetect()}>
              Run detection
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {rows.map((a, i) => (
            <motion.div
              key={String(a.id)}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: Math.min(i * 0.03, 0.3) }}
            >
              <Card className="h-full transition hover:border-[var(--accent)]/25">
                <CardContent className="space-y-3 p-5">
                  <div className="flex items-center justify-between gap-2">
                    <Badge tone={sevTone(a.severity)}>{a.severity}</Badge>
                    <span className="font-mono text-xs text-[var(--muted)]">
                      {(a.detection_date ?? "").slice(0, 10)}
                    </span>
                  </div>
                  <p className="text-sm font-semibold leading-snug">{a.description}</p>
                  <div className="flex flex-wrap gap-2 text-xs text-[var(--muted)]">
                    <span>{a.anomaly_type}</span>
                    <span>·</span>
                    <span>{a.store_id ?? "Enterprise"}</span>
                    <span>·</span>
                    <span>score {a.score?.toFixed(3)}</span>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
