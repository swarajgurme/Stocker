import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ShoppingCart, Calendar, Truck, Package, ShieldAlert } from "lucide-react";
import { procurementAPI, type ProcurementCardRow } from "@/services/api";
import { PageHeader } from "@/components/ui/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PageSkeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";

export default function RecommendationsPage() {
  const [procurementCards, setProcurementCards] = useState<ProcurementCardRow[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const res = await procurementAPI.recommendations();
      setProcurementCards(res.data.recommendations);
    } catch {
      setProcurementCards([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <PageHeader
        title="Procurement & Action Directives"
        description="Pillar 3: Actionable purchase recommendations derived from forecast demand, EOQ optimization, supplier lead times, and anomaly flags."
        actions={
          <Button type="button" variant="outline" onClick={() => void load()}>
            Refresh Directives
          </Button>
        }
      />

      {loading ? (
        <PageSkeleton />
      ) : procurementCards.length === 0 ? (
        <EmptyState
          icon={ShoppingCart}
          title="All Procurement Up to Date"
          description="Current store stock levels breach neither Reorder Points nor Safety Stock boundaries."
          action={
            <Button type="button" onClick={() => void load()}>
              Refresh Procurement Cards
            </Button>
          }
        />
      ) : (
        <div className="grid gap-6 md:grid-cols-2">
          {procurementCards.map((card, i) => (
            <motion.div
              key={card.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <Card glow className="h-full flex flex-col justify-between overflow-hidden border border-slate-800 bg-slate-900/60 backdrop-blur-md">
                <CardHeader className="pb-3">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <Package className="h-4 w-4 text-emerald-400" />
                        <CardTitle className="text-base font-semibold text-slate-100">
                          {card.product_name}
                        </CardTitle>
                      </div>
                      <p className="mt-1 text-xs text-slate-400">
                        SKU: <span className="font-mono text-slate-300">{card.sku}</span> · Category: {card.category} · Store: {card.store_id}
                      </p>
                    </div>

                    <div className="flex flex-wrap gap-1.5">
                      {card.urgent_review_flag && (
                        <Badge tone="critical" className="animate-pulse flex items-center gap-1">
                          <ShieldAlert className="h-3 w-3" /> Urgent Review
                        </Badge>
                      )}
                      <Badge tone={card.status === "ORDER_NOW" ? "warning" : "muted"}>
                        {card.status === "ORDER_NOW" ? "ORDER NOW" : "PLANNED"}
                      </Badge>
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="space-y-4 text-sm">
                  {/* Grid of Key Procurement Metrics */}
                  <div className="grid grid-cols-2 gap-3 rounded-lg bg-slate-950/50 p-3 border border-slate-800/80">
                    <div>
                      <span className="text-xs text-slate-400 block font-medium">How Much to Order (EOQ)</span>
                      <span className="text-lg font-bold text-emerald-400">{card.order_quantity} units</span>
                    </div>
                    <div>
                      <span className="text-xs text-slate-400 block font-medium">Order-By Date</span>
                      <span className="text-base font-semibold text-amber-400 flex items-center gap-1 mt-0.5">
                        <Calendar className="h-3.5 w-3.5 inline" /> {card.order_by_date}
                      </span>
                    </div>
                    <div>
                      <span className="text-xs text-slate-400 block font-medium">Supplier</span>
                      <span className="text-xs font-semibold text-slate-200 flex items-center gap-1 mt-0.5">
                        <Truck className="h-3.5 w-3.5 inline text-sky-400" /> {card.supplier_name}
                      </span>
                    </div>
                    <div>
                      <span className="text-xs text-slate-400 block font-medium">Lead Time</span>
                      <span className="text-xs font-semibold text-slate-200 mt-0.5 block">
                        {card.lead_time_days} Days
                      </span>
                    </div>
                  </div>

                  {/* Rationale Section */}
                  <div className="rounded-md bg-slate-950/30 p-2.5 border border-slate-800/40 text-xs">
                    <span className="font-semibold text-slate-300 block mb-0.5">Why (Decision Rationale):</span>
                    <p className="text-slate-400 leading-relaxed">{card.reason}</p>
                    <div className="mt-2 flex gap-4 text-[11px] text-slate-500 font-mono">
                      <span>Current Stock: {card.current_stock}</span>
                      <span>Reorder Point: {card.reorder_point}</span>
                      <span>Safety Stock: {card.safety_stock}</span>
                    </div>
                  </div>

                  <div className="pt-1 flex items-center justify-between">
                    <span className="text-xs text-slate-500">Pillar 3 Procurement Engine</span>
                    <Button size="sm" variant="primary" className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs">
                      Issue Purchase Order ({card.order_quantity} Units)
                    </Button>
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
