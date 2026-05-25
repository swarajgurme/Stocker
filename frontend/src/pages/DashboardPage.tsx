import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Activity, AlertTriangle, Gauge, TrendingUp } from "lucide-react";
import {
  analyticsAPI,
  recommendationAPI,
  type DashboardPayload,
  type RecommendationRow,
} from "@/services/api";
import { PageHeader } from "@/components/ui/page-header";
import { StatCard } from "@/components/ui/stat-card";
import { ChartCard } from "@/components/ui/chart-card";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageSkeleton } from "@/components/ui/skeleton";
import { Alert } from "@/components/ui/alert";
import {
  CHART_ACCENT,
  CHART_AXIS,
  CHART_GRID,
  CHART_VIOLET,
  chartTooltipStyle,
} from "@/lib/chart-theme";

export default function DashboardPage() {
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [recs, setRecs] = useState<RecommendationRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [recErr, setRecErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      setLoading(true);
      setErr(null);
      try {
        const d = await analyticsAPI.dashboard();
        if (alive) setData(d.data);
      } catch (e: unknown) {
        const code = (e as { status?: number }).status;
        setErr(
          code === 403
            ? "Executive dashboard requires administrator, analyst, or executive role."
            : (e as Error).message ?? "Failed to load KPIs",
        );
      } finally {
        if (alive) setLoading(false);
      }
      try {
        const r = await recommendationAPI.list();
        if (alive) setRecs(r.data.recommendations.slice(0, 6));
      } catch (e: unknown) {
        setRecErr((e as Error).message ?? "Recommendations unavailable");
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  if (loading) return <PageSkeleton />;
  if (err || !data) {
    return (
      <div className="mx-auto max-w-lg">
        <Alert variant="info" title="Dashboard unavailable">
          {err}
        </Alert>
      </div>
    );
  }

  const rev = data.revenue_trend.map((r) => ({ label: r.month, revenue: r.revenue }));

  return (
    <div className="mx-auto max-w-7xl space-y-8">
      <PageHeader
        title="Executive command center"
        description="Supply chain health, revenue motion, inventory risk, and prioritized AI directives in one operational view."
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Inventory turnover"
          value={data.inventory_turnover.toFixed(2)}
          hint="Units sold / avg on-hand"
          icon={Activity}
          delay={0}
        />
        <StatCard
          label="Forecast quality"
          value={`${data.forecast_accuracy.avg_mape.toFixed(1)}% MAPE`}
          hint={data.forecast_accuracy.interpretation}
          icon={TrendingUp}
          trend={data.forecast_accuracy.avg_mape < 12 ? "up" : "neutral"}
          delay={0.05}
        />
        <StatCard
          label="Low-stock positions"
          value={String(data.low_stock_count)}
          hint="Below safety stock"
          icon={AlertTriangle}
          trend={data.low_stock_count > 10 ? "down" : "neutral"}
          delay={0.1}
        />
        <StatCard
          label="Demand risk score"
          value={String(data.demand_risk_score)}
          hint={`${data.anomalies_open} open anomalies · ${data.active_stores} stores`}
          icon={Gauge}
          delay={0.15}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <ChartCard title="Revenue analytics" badge="Trailing 12 months" className="lg:col-span-2">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={rev}>
              <defs>
                <linearGradient id="revG" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={CHART_ACCENT} stopOpacity={0.45} />
                  <stop offset="95%" stopColor={CHART_ACCENT} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="4 6" stroke={CHART_GRID} />
              <XAxis dataKey="label" stroke={CHART_AXIS} tick={{ fontSize: 11 }} />
              <YAxis stroke={CHART_AXIS} tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={chartTooltipStyle()} />
              <Area
                type="monotone"
                dataKey="revenue"
                stroke={CHART_ACCENT}
                strokeWidth={2}
                fill="url(#revG)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Top stores" description="Revenue by location">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.top_stores}>
              <CartesianGrid strokeDasharray="4 6" stroke={CHART_GRID} vertical={false} />
              <XAxis dataKey="store_id" stroke={CHART_AXIS} tick={{ fontSize: 11 }} />
              <YAxis stroke={CHART_AXIS} tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={chartTooltipStyle()} />
              <Bar dataKey="revenue" fill={CHART_ACCENT} radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <ChartCard title="Category mix">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.category_performance}>
              <CartesianGrid strokeDasharray="4 6" stroke={CHART_GRID} vertical={false} />
              <XAxis dataKey="category" stroke={CHART_AXIS} tick={{ fontSize: 10 }} />
              <YAxis stroke={CHART_AXIS} tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={chartTooltipStyle()} />
              <Bar dataKey="revenue" fill={CHART_VIOLET} radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <Card glow>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>AI recommendation feed</CardTitle>
            <Badge>Live</Badge>
          </CardHeader>
          <CardContent className="max-h-80 space-y-3 overflow-y-auto">
            {recErr ? (
              <p className="text-sm text-[var(--muted)]">{recErr}</p>
            ) : recs.length === 0 ? (
              <p className="text-sm text-[var(--muted)]">No active recommendations yet.</p>
            ) : (
              recs.map((r) => (
                <div
                  key={r.id}
                  className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface2)] p-3 transition hover:border-[var(--accent)]/30"
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-semibold">{r.title}</p>
                    <Badge tone="default">{Math.round(r.confidence_score * 100)}%</Badge>
                  </div>
                  <p className="mt-1 text-xs text-[var(--muted)]">
                    {r.store_id ?? "—"} · {r.product_name ?? "Network"}
                  </p>
                  <p className="mt-2 line-clamp-2 text-xs text-[var(--text-secondary)]">
                    {r.description}
                  </p>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
