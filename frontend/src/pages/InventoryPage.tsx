import { useEffect, useMemo, useState } from "react";
import { RefreshCw, Search, Calculator } from "lucide-react";
import { inventoryAPI, STORES, type InventoryRow, type InventoryOptimizationResult } from "@/services/api";
import { useTable } from "@/hooks/useTable";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataTable, type Column } from "@/components/ui/data-table";
import { PageSkeleton } from "@/components/ui/skeleton";
import { Alert } from "@/components/ui/alert";
import { Label } from "@/components/ui/label";

const statusTone = (status: string) =>
  status === "critical" ? "critical" : status === "warning" ? "warning" : "healthy";

export default function InventoryPage() {
  const [rows, setRows] = useState<InventoryRow[]>([]);
  const [alertsOnly, setAlertsOnly] = useState(false);
  const [store, setStore] = useState("");
  const [selectedProductOpt, setSelectedProductOpt] = useState<InventoryOptimizationResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {};
      if (store) params.store_id = store;
      if (alertsOnly) params.low_stock_only = "true";
      const res = await inventoryAPI.list(params);
      setRows(res.data.inventory);
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [store, alertsOnly]);

  const loadOptimizationDetails = async (productId: number) => {
    try {
      const res = await inventoryAPI.optimization(productId);
      setSelectedProductOpt(res.data);
    } catch (e: unknown) {
      setError((e as Error).message);
    }
  };

  const table = useTable(rows, {
    pageSize: 14,
    searchKeys: ["product_name", "category", "store_id"],
    initialSort: { key: "current_stock", dir: "asc" },
  });

  const columns: Column<InventoryRow>[] = useMemo(
    () => [
      { key: "store_id", header: "Store", sortable: true },
      { key: "product_name", header: "SKU / Material", sortable: true },
      { key: "category", header: "Category", sortable: true },
      {
        key: "current_stock",
        header: "On Hand",
        sortable: true,
        align: "right",
        render: (r) => <span className="font-semibold text-slate-100">{r.current_stock}</span>,
      },
      {
        key: "safety_stock",
        header: "Safety Stock",
        sortable: true,
        align: "right",
        render: (r) => r.safety_stock.toFixed(0),
      },
      {
        key: "reorder_point",
        header: "Reorder Point (ROP)",
        sortable: true,
        align: "right",
        render: (r) => (
          <span className="font-semibold text-amber-400">{r.reorder_point.toFixed(0)}</span>
        ),
      },
      {
        key: "lead_time_days",
        header: "Lead Time",
        sortable: true,
        align: "right",
        render: (r) => `${r.lead_time_days}d`,
      },
      {
        key: "status",
        header: "Status",
        render: (r) => <Badge tone={statusTone(r.status)}>{r.status}</Badge>,
      },
      {
        key: "id",
        header: "EOQ Math",
        align: "right",
        render: (r) => (
          <Button
            size="sm"
            variant="ghost"
            className="text-xs text-emerald-400 hover:text-emerald-300 hover:bg-emerald-950/40"
            onClick={() => void loadOptimizationDetails(r.id)}
          >
            <Calculator className="h-3.5 w-3.5 mr-1 inline" /> Calc EOQ
          </Button>
        ),
      },
    ],
    [],
  );

  const criticalCount = rows.filter((r) => r.status === "critical").length;

  return (
    <div className="mx-auto max-w-7xl space-y-8">
      <PageHeader
        title="Inventory Optimization (ROP + EOQ)"
        description="Pillar 4: Operations research mathematics minimizing holding & ordering costs. ROP answers WHEN to reorder; EOQ answers HOW MUCH."
        actions={
          <Button variant="outline" size="sm" type="button" onClick={() => void load()}>
            <RefreshCw className="h-4 w-4 mr-1" /> Refresh Stock
          </Button>
        }
      />

      {/* Selected Product EOQ Optimization Math Modal/Panel */}
      {selectedProductOpt && (
        <Card className="border border-emerald-800/80 bg-slate-900/90 backdrop-blur-md glow">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle className="text-base font-bold text-emerald-400 flex items-center gap-2">
                <Calculator className="h-5 w-5" /> Inventory Optimization Breakdown: {selectedProductOpt.product_name}
              </CardTitle>
              <p className="text-xs text-slate-400">SKU: {selectedProductOpt.sku} · Category: {selectedProductOpt.category}</p>
            </div>
            <Button size="sm" variant="ghost" onClick={() => setSelectedProductOpt(null)}>Close</Button>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 bg-slate-950/60 p-4 rounded-lg border border-slate-800">
              <div>
                <span className="text-xs text-slate-400 block">Current Stock</span>
                <span className="text-lg font-bold text-slate-100">{selectedProductOpt.current_stock} units</span>
              </div>
              <div>
                <span className="text-xs text-slate-400 block">Reorder Point (ROP - WHEN)</span>
                <span className="text-lg font-bold text-amber-400">{selectedProductOpt.calculated_rop} units</span>
              </div>
              <div>
                <span className="text-xs text-slate-400 block font-semibold text-emerald-300">Economic Order Qty (EOQ - HOW MUCH)</span>
                <span className="text-xl font-extrabold text-emerald-400">{selectedProductOpt.calculated_eoq} units</span>
              </div>
              <div>
                <span className="text-xs text-slate-400 block">Supplier Lead Time</span>
                <span className="text-lg font-bold text-sky-400">{selectedProductOpt.lead_time_days} Days ({selectedProductOpt.supplier_name})</span>
              </div>
            </div>

            <div className="rounded bg-slate-950/40 p-3 border border-slate-800 text-xs text-slate-300 font-mono space-y-1">
              <p className="font-semibold text-emerald-300 mb-1">EOQ Formula: √((2 × Annual Demand × Ordering Cost) / Holding Cost)</p>
              <p>· Annual Demand (D): {selectedProductOpt.annual_demand} units/year</p>
              <p>· Ordering Cost (S): ${selectedProductOpt.ordering_cost} per purchase order</p>
              <p>· Holding Cost (H): ${selectedProductOpt.holding_cost_per_unit} /unit/year</p>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Inventory Filters & Search</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4 lg:flex-row lg:items-end">
          <Label className="lg:w-44">
            Store Location
            <Select className="mt-1" value={store} onChange={(e) => setStore(e.target.value)}>
              <option value="">All stores</option>
              {STORES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </Select>
          </Label>
          <label className="flex cursor-pointer items-center gap-2 pb-2 text-sm text-[var(--text-secondary)]">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-[var(--border)] accent-[var(--accent)]"
              checked={alertsOnly}
              onChange={(e) => setAlertsOnly(e.target.checked)}
            />
            Low stock breaches only
          </label>
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--muted)]" />
            <Input
              className="pl-9"
              placeholder="Search product or category…"
              value={table.query}
              onChange={(e) => table.setQuery(e.target.value)}
            />
          </div>
          {criticalCount > 0 ? (
            <Badge tone="critical">{criticalCount} critical breaches</Badge>
          ) : null}
        </CardContent>
      </Card>

      {loading ? (
        <PageSkeleton />
      ) : error ? (
        <Alert variant="error">{error}</Alert>
      ) : (
        <DataTable
          columns={columns}
          data={table.pageData}
          sort={table.sort}
          onSort={table.toggleSort}
          page={table.page}
          totalPages={table.totalPages}
          total={table.total}
          pageSize={table.pageSize}
          onPageChange={table.setPage}
        />
      )}
    </div>
  );
}
