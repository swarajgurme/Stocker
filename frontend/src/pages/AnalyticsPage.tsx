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
import { ArrowRightLeft, PackageCheck, Truck } from "lucide-react";
import { analyticsAPI, planningAPI, CATEGORIES, type ClusterRow, type StockTransferRow } from "@/services/api";
import { PageHeader } from "@/components/ui/page-header";
import { StatCard } from "@/components/ui/stat-card";
import { ChartCard } from "@/components/ui/chart-card";
import { PageSkeleton } from "@/components/ui/skeleton";
import { Alert } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
  const [transfers, setTransfers] = useState<StockTransferRow[]>([]);
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
        const t = await planningAPI.transfers();
        if (a) {
          setClusters(c.data.assignments);
          setStats(c.data.statistics);
          setRegional(r.data);
          setTransfers(t.data.transfers);
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
        title="Supply Chain Planning & Network Optimization"
        description="Pillar 2: Inter-store stock transfer directives to balance network inventory before purchasing, alongside K-Means store segmentation."
      />

      {/* Network Stock Transfer Planning Directives Card Section */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <ArrowRightLeft className="h-5 w-5 text-emerald-400" />
          <h2 className="text-lg font-semibold text-slate-100">
            Recommended Inter-Store Stock Transfers ({transfers.length})
          </h2>
        </div>

        {transfers.length === 0 ? (
          <Card className="border border-slate-800 bg-slate-900/40 p-6 text-center text-slate-400">
            <PackageCheck className="mx-auto h-8 w-8 text-emerald-400 mb-2" />
            <p className="text-sm font-medium">Network Inventory Balanced</p>
            <p className="text-xs text-slate-500 mt-1">No store currently requires internal stock transfers from surplus locations.</p>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {transfers.map((t) => (
              <Card key={t.id} className="border border-slate-800 bg-slate-900/60 backdrop-blur-md">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base font-semibold text-slate-200">
                      {t.product_name}
                    </CardTitle>
                    <Badge tone={t.urgency === "High" ? "critical" : "warning"}>
                      {t.urgency} Urgency
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-400 font-mono">SKU: {t.sku}</p>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <div className="flex items-center justify-between rounded-lg bg-slate-950/60 p-3 border border-slate-800">
                    <div className="text-center">
                      <span className="text-[11px] text-slate-400 block font-medium">Source (Surplus)</span>
                      <span className="text-sm font-bold text-amber-400 flex items-center gap-1 mt-0.5 justify-center">
                        <Truck className="h-3.5 w-3.5" /> {t.source_store_name} ({t.source_store_id})
                      </span>
                    </div>

                    <ArrowRightLeft className="h-5 w-5 text-emerald-400 animate-pulse" />

                    <div className="text-center">
                      <span className="text-[11px] text-slate-400 block font-medium">Target (Low Stock)</span>
                      <span className="text-sm font-bold text-emerald-400 mt-0.5 block">
                        {t.target_store_name} ({t.target_store_id})
                      </span>
                    </div>
                  </div>

                  <div className="rounded bg-emerald-950/20 border border-emerald-800/40 p-2.5 text-xs text-emerald-300">
                    <span className="font-semibold block mb-0.5">Transfer Quantity: {t.quantity} Units</span>
                    <p className="text-slate-300">{t.directive}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {stats ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5 pt-4">
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
        <ChartCard title="K-Means Store Cluster Landscape" description="Sales EWMA vs product category segment">
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

        <ChartCard title="Category Concentration" description="Trailing year sales revenue">
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
