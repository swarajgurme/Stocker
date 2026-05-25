import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { motion } from "framer-motion";
import { LineChart as LineChartIcon } from "lucide-react";
import { forecastAPI, PRODUCTS, STORES, type ForecastGenerateResult } from "@/services/api";
import { PageHeader } from "@/components/ui/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { Alert } from "@/components/ui/alert";
import { ChartCard } from "@/components/ui/chart-card";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import {
  CHART_ACCENT,
  CHART_AXIS,
  CHART_GRID,
  CHART_VIOLET,
  chartTooltipStyle,
} from "@/lib/chart-theme";

const models = [
  { value: "auto", label: "Auto-select" },
  { value: "prophet", label: "Prophet" },
  { value: "arima", label: "ARIMA" },
  { value: "xgboost", label: "XGBoost" },
];

export default function ForecastPage() {
  const [store, setStore] = useState("S001");
  const [product, setProduct] = useState("Battery");
  const [start, setStart] = useState("2024-01-01");
  const [end, setEnd] = useState("2024-12-31");
  const [model, setModel] = useState("auto");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ForecastGenerateResult | null>(null);

  const chartData = useMemo(() => {
    if (!result) return [];
    return result.forecast.map((f) => ({
      date: f.date,
      predicted: f.predicted,
      lower: f.lower_bound,
      upper: f.upper_bound,
    }));
  }, [result]);

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await forecastAPI.generate({
        store_id: store,
        product_name: product,
        start_date: start,
        end_date: end,
        horizon_days: 120,
        model_type: model,
      });
      setResult(res.data);
    } catch (e: unknown) {
      setError((e as Error).message ?? "Forecast failed");
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <PageHeader
        title="Demand forecasting"
        description="Multi-model forecasting with confidence envelopes and error metrics."
      />

      <Card glow>
        <CardHeader>
          <CardTitle>Forecast configuration</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Label>
            Store
            <Select className="mt-1" value={store} onChange={(e) => setStore(e.target.value)}>
              {STORES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </Select>
          </Label>
          <Label>
            Product
            <Select className="mt-1" value={product} onChange={(e) => setProduct(e.target.value)}>
              {PRODUCTS.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </Select>
          </Label>
          <Label>
            Model
            <Select className="mt-1" value={model} onChange={(e) => setModel(e.target.value)}>
              {models.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </Select>
          </Label>
          <Label>
            History start
            <Input type="date" className="mt-1" value={start} onChange={(e) => setStart(e.target.value)} />
          </Label>
          <Label>
            History end
            <Input type="date" className="mt-1" value={end} onChange={(e) => setEnd(e.target.value)} />
          </Label>
          <div className="flex items-end">
            <Button type="button" className="w-full" size="lg" onClick={() => void run()} disabled={loading}>
              {loading ? <Spinner className="h-5 w-5" /> : "Generate forecast"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {error ? <Alert variant="error">{error}</Alert> : null}

      {result ? (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          <ChartCard
            title={`${result.product_name} · ${result.store_id}`}
            description={`Model ${result.model_type} · ${result.execution_time_seconds}s runtime`}
            badge="120-day horizon"
            height="h-[26rem]"
          >
            <div className="mb-4 flex flex-wrap gap-2">
              <MetricPill label="RMSE" v={result.metrics.rmse} />
              <MetricPill label="MAE" v={result.metrics.mae} />
              <MetricPill label="MAPE %" v={result.metrics.mape} />
            </div>
            <ResponsiveContainer width="100%" height="85%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="4 6" stroke={CHART_GRID} />
                <XAxis dataKey="date" stroke={CHART_AXIS} tick={{ fontSize: 10 }} />
                <YAxis stroke={CHART_AXIS} tick={{ fontSize: 10 }} />
                <Tooltip contentStyle={chartTooltipStyle()} />
                <Legend />
                <Line type="monotone" dataKey="predicted" stroke={CHART_ACCENT} strokeWidth={2} dot={false} name="Predicted" />
                <Line type="monotone" dataKey="upper" stroke={CHART_VIOLET} strokeDasharray="4 4" dot={false} name="Upper CI" />
                <Line type="monotone" dataKey="lower" stroke={CHART_VIOLET} strokeDasharray="4 4" dot={false} name="Lower CI" />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>
        </motion.div>
      ) : (
        !loading && (
          <EmptyState
            icon={LineChartIcon}
            title="No forecast yet"
            description="Configure store, product, and date range, then generate a demand forecast."
          />
        )
      )}
    </div>
  );
}

function MetricPill({ label, v }: { label: string; v: number | null | undefined }) {
  return (
    <Badge tone="muted" className="normal-case tracking-normal">
      {label}:{" "}
      <span className="font-mono text-[var(--text)]">
        {v == null ? "—" : typeof v === "number" ? v.toFixed(3) : String(v)}
      </span>
    </Badge>
  );
}
