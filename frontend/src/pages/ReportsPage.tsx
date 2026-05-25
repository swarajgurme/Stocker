import { useState } from "react";
import { FileSpreadsheet, FileText, Table2 } from "lucide-react";
import { reportAPI, downloadAuthorizedFile } from "@/services/api";
import { PageHeader } from "@/components/ui/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { Alert } from "@/components/ui/alert";

const formats = [
  { id: "csv" as const, label: "CSV summary", desc: "Lightweight tabular export", icon: Table2 },
  { id: "excel" as const, label: "Excel workbook", desc: "Multi-sheet executive pack", icon: FileSpreadsheet },
  { id: "pdf" as const, label: "PDF report", desc: "Print-ready (WeasyPrint on server)", icon: FileText },
];

export default function ReportsPage() {
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const run = async (format: "csv" | "pdf" | "excel") => {
    setBusy(format);
    setMsg(null);
    try {
      const res = await reportAPI.generate({
        report_type: "executive_summary",
        format,
        include_forecasts: true,
        include_inventory: true,
      });
      const blob = await downloadAuthorizedFile(res.data.download_url);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `stocker_report.${format === "excel" ? "xlsx" : format}`;
      a.click();
      URL.revokeObjectURL(url);
      setMsg({ type: "success", text: "Report generated and downloaded." });
    } catch (e: unknown) {
      setMsg({ type: "error", text: (e as Error).message });
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <PageHeader
        title="Report center"
        description="Executive-ready exports with inventory and forecast context."
      />

      {msg ? (
        <Alert variant={msg.type === "success" ? "success" : "error"}>{msg.text}</Alert>
      ) : null}

      <div className="grid gap-4">
        {formats.map((f) => {
          const Icon = f.icon;
          return (
            <Card key={f.id} className="transition hover:border-[var(--accent)]/30">
              <CardHeader className="flex flex-row items-center gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[var(--accent)]/10 text-[var(--accent)]">
                  <Icon className="h-6 w-6" />
                </div>
                <div className="flex-1">
                  <CardTitle className="text-base">{f.label}</CardTitle>
                  <CardDescription>{f.desc}</CardDescription>
                </div>
                <Button
                  type="button"
                  variant={f.id === "csv" ? "primary" : "outline"}
                  disabled={busy !== null}
                  onClick={() => void run(f.id)}
                >
                  {busy === f.id ? <Spinner className="h-5 w-5" /> : "Download"}
                </Button>
              </CardHeader>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
