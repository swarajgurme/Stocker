import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import { analyticsAPI, CATEGORIES, type ClusterRow } from "@/services/api";
import { PageHeader } from "@/components/ui/page-header";
import { StatCard } from "@/components/ui/stat-card";
import { ChartCard } from "@/components/ui/chart-card";
import { PageSkeleton } from "@/components/ui/skeleton";
import { Alert } from "@/components/ui/alert";
import {
  CHART_ACCENT,
  CHART_AXIS,
  CHART_GRID,
  CHART_PALETTE,
  chartTooltipStyle,
} from "@/lib/chart-theme";

const catIndex = Object.fromEntries(CATEGORIES.map((c, i) => [c, i])) as Record<string, number>;

export default function AnalyticsPage() {
  const [clusters, setClusters] = useState<ClusterRow[]>([]);
  const [stats, setStats] = useState<Record<string, { count: number; avg_sales: number }> | null>(
    null,
  );
  const [regional, setRegional] = useState<
    Array<{ category: string; total_sales: number; units: number }>
  >([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let a = true;
    (async () => {
      setLoading(true);
      setErr(null);
      try {
        const c = await analyticsAPI.clusters();
        const r = await analyticsAPI.salesByCategory("last_year");
        if (a) {
          setClusters(c.data.assignments);
          setStats(c.data.statistics);
          setRegional(r.data);
        }
      } catch (e: unknown) {
        setErr((e as Error).message);
      } finally {
        if (a) setLoading(false);
      }
    })();
    return () => {
      a = false;
    };
  }, []);

  const scatter = useMemo(
    () =>
      clusters.map((row) => ({
        x: row.sales_ewma,
        y: catIndex[row.category] ?? 0,
        z: row.cluster,
        label: `${row.store_id} · ${row.category}`,
      })),
    [clusters],
  );

  if (loading) return <PageSkeleton />;
  if (err) return <Alert variant="error">{err}</Alert>;

  return (
    <div className="mx-auto max-w-7xl space-y-8">
      <PageHeader
        title="Advanced analytics"
        description="Portfolio segmentation via K-means clusters and regional revenue structure."
      />

      {stats ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {Object.entries(stats).map(([k, v], i) => (
            <StatCard
              key={k}
              label={`Cluster ${k}`}
              value={String(v.count)}
              hint={`Avg signal ${v.avg_sales.toFixed(2)}`}
              delay={i * 0.04}
            />
          ))}
        </div>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-2">
        <ChartCard title="Cluster landscape" description="EWMA vs category segment">
          {scatter.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">Run cluster analysis from the API to populate.</p>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 12 }}>
                <CartesianGrid strokeDasharray="4 6" stroke={CHART_GRID} />
                <XAxis type="number" dataKey="x" name="EWMA" stroke={CHART_AXIS} tick={{ fontSize: 10 }} />
                <YAxis
                  type="number"
                  dataKey="y"
                  stroke={CHART_AXIS}
                  ticks={[0, 1, 2, 3, 4]}
                  tickFormatter={(v: number) => CATEGORIES[v] ?? String(v)}
                />
                <ZAxis type="number" dataKey="z" range={[60, 400]} />
                <Tooltip cursor={{ strokeDasharray: "3 3" }} contentStyle={chartTooltipStyle()} />
                <Scatter data={scatter}>
                  {scatter.map((e, i) => (
                    <Cell key={`c-${i}`} fill={CHART_PALETTE[e.z % CHART_PALETTE.length]} />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        <ChartCard title="Category concentration" description="Trailing year revenue">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={regional} layout="vertical" margin={{ left: 32 }}>
              <CartesianGrid strokeDasharray="4 6" stroke={CHART_GRID} horizontal={false} />
              <XAxis type="number" stroke={CHART_AXIS} tick={{ fontSize: 10 }} />
              <YAxis type="category" dataKey="category" stroke={CHART_AXIS} width={100} tick={{ fontSize: 10 }} />
              <Tooltip contentStyle={chartTooltipStyle()} />
              <Bar dataKey="total_sales" fill={CHART_ACCENT} radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  );
}
