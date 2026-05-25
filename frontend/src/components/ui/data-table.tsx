import { ChevronDown, ChevronLeft, ChevronRight, ChevronUp } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { SortDir } from "@/hooks/useTable";

export type Column<T> = {
  key: keyof T | string;
  header: string;
  sortable?: boolean;
  align?: "left" | "right";
  render?: (row: T) => ReactNode;
  className?: string;
};

export function DataTable<T extends { id?: number | string }>({
  columns,
  data,
  sort,
  onSort,
  page,
  totalPages,
  total,
  pageSize,
  onPageChange,
  emptyMessage = "No records found",
}: {
  columns: Column<T>[];
  data: T[];
  sort?: { key: keyof T; dir: SortDir };
  onSort?: (key: keyof T) => void;
  page: number;
  totalPages: number;
  total: number;
  pageSize: number;
  onPageChange: (p: number) => void;
  emptyMessage?: string;
}) {
  if (data.length === 0) {
    return (
      <div className="rounded-[var(--radius-lg)] border border-dashed border-[var(--border)] py-16 text-center text-sm text-[var(--muted)]">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="glass-panel overflow-hidden rounded-[var(--radius-lg)]">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="sticky top-0 z-10 border-b border-[var(--border)] bg-[var(--surface-solid)]/95 backdrop-blur">
            <tr>
              {columns.map((col) => {
                const key = col.key as keyof T;
                const active = sort?.key === key;
                return (
                  <th
                    key={String(col.key)}
                    className={cn(
                      "px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-[var(--muted)]",
                      col.align === "right" && "text-right",
                      col.sortable && "cursor-pointer select-none hover:text-[var(--text)]",
                      col.className,
                    )}
                    onClick={() => col.sortable && onSort?.(key)}
                  >
                    <span className="inline-flex items-center gap-1">
                      {col.header}
                      {col.sortable && active ? (
                        sort.dir === "asc" ? (
                          <ChevronUp className="h-3 w-3" />
                        ) : (
                          <ChevronDown className="h-3 w-3" />
                        )
                      ) : null}
                    </span>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border)]">
            {data.map((row, i) => (
              <tr
                key={String(row.id ?? i)}
                className="transition-colors hover:bg-[var(--surface-hover)]"
              >
                {columns.map((col) => (
                  <td
                    key={String(col.key)}
                    className={cn(
                      "px-4 py-3 text-[var(--text-secondary)]",
                      col.align === "right" && "text-right tabular-nums",
                      col.className,
                    )}
                  >
                    {col.render
                      ? col.render(row)
                      : String((row as Record<string, unknown>)[col.key as string] ?? "—")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {totalPages > 1 ? (
        <div className="flex items-center justify-between border-t border-[var(--border)] px-4 py-3 text-xs text-[var(--muted)]">
          <span>
            {page * pageSize + 1}–{Math.min((page + 1) * pageSize, total)} of {total}
          </span>
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="icon"
              type="button"
              disabled={page <= 0}
              onClick={() => onPageChange(page - 1)}
              aria-label="Previous page"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              type="button"
              disabled={page >= totalPages - 1}
              onClick={() => onPageChange(page + 1)}
              aria-label="Next page"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
