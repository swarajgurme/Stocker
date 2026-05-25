import { useEffect, useMemo, useState } from "react";
import { RefreshCw, Search } from "lucide-react";
import { inventoryAPI, STORES, type InventoryRow } from "@/services/api";
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

  const table = useTable(rows, {
    pageSize: 14,
    searchKeys: ["product_name", "category", "store_id"],
    initialSort: { key: "current_stock", dir: "asc" },
  });

  const columns: Column<InventoryRow>[] = useMemo(
    () => [
      { key: "store_id", header: "Store", sortable: true },
      { key: "product_name", header: "SKU", sortable: true },
      { key: "category", header: "Category", sortable: true },
      {
        key: "current_stock",
        header: "On hand",
        sortable: true,
        align: "right",
        render: (r) => r.current_stock,
      },
      {
        key: "safety_stock",
        header: "Safety",
        sortable: true,
        align: "right",
        render: (r) => r.safety_stock.toFixed(0),
      },
      {
        key: "reorder_point",
        header: "Reorder",
        sortable: true,
        align: "right",
        render: (r) => r.reorder_point.toFixed(0),
      },
      {
        key: "status",
        header: "Status",
        render: (r) => <Badge tone={statusTone(r.status)}>{r.status}</Badge>,
      },
    ],
    [],
  );

  const criticalCount = rows.filter((r) => r.status === "critical").length;

  return (
    <div className="mx-auto max-w-7xl space-y-8">
      <PageHeader
        title="Inventory intelligence"
        description="Live stock posture, reorder alignment, and risk indicators by store SKU."
        actions={
          <Button variant="outline" size="sm" type="button" onClick={() => void load()}>
            <RefreshCw className="h-4 w-4" /> Refresh
          </Button>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4 lg:flex-row lg:items-end">
          <Label className="lg:w-44">
            Store
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
            Low stock only
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
            <Badge tone="critical">{criticalCount} critical</Badge>
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
