import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";
import { recommendationAPI, type RecommendationRow } from "@/services/api";
import { PageHeader } from "@/components/ui/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { PageSkeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";

export default function RecommendationsPage() {
  const [rows, setRows] = useState<RecommendationRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [genBusy, setGenBusy] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await recommendationAPI.list();
      setRows(r.data.recommendations);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const generate = async () => {
    setGenBusy(true);
    try {
      await recommendationAPI.generate({});
      await load();
    } finally {
      setGenBusy(false);
    }
  };

  const act = async (id: number) => {
    await recommendationAPI.act(id, "Acknowledged from console");
    await load();
  };

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <PageHeader
        title="AI recommendations"
        description="Inventory, procurement, and demand balancing guidance with explicit confidence."
        actions={
          <Button type="button" variant="outline" onClick={() => void generate()} disabled={genBusy}>
            {genBusy ? <Spinner className="h-5 w-5" /> : "Regenerate queue"}
          </Button>
        }
      />

      {loading ? (
        <PageSkeleton />
      ) : rows.length === 0 ? (
        <EmptyState
          icon={Sparkles}
          title="No recommendations yet"
          description="Generate forecasts first, then regenerate the AI action queue."
          action={
            <Button type="button" onClick={() => void generate()}>
              Regenerate queue
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4">
          {rows.map((r, i) => (
            <motion.div
              key={r.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
            >
              <Card glow className="overflow-hidden">
                <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-2">
                  <div>
                    <CardTitle className="text-base">{r.title}</CardTitle>
                    <p className="text-xs text-[var(--muted)]">
                      {r.store_id ?? "—"} · {r.product_name ?? "—"}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Badge tone="muted">P{r.priority}</Badge>
                    <Badge>{Math.round(r.confidence_score * 100)}% conf</Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3 text-sm text-[var(--text-secondary)]">
                  <p>{r.description}</p>
                  {r.rationale ? <p className="text-xs italic text-[var(--muted)]">{r.rationale}</p> : null}
                  {r.expected_impact ? (
                    <p className="text-xs font-medium text-[var(--accent)]">Impact: {r.expected_impact}</p>
                  ) : null}
                  <Button size="sm" variant="ghost" type="button" onClick={() => void act(r.id)}>
                    Mark acted
                  </Button>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
