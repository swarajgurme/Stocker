import { useMemo, useState } from "react";

export type SortDir = "asc" | "desc";

export function useTable<T>(
  data: T[],
  options: {
    pageSize?: number;
    searchKeys?: (keyof T)[];
    initialSort?: { key: keyof T; dir: SortDir };
  } = {},
) {
  const { pageSize = 12, searchKeys = [], initialSort } = options;
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const [sort, setSort] = useState(initialSort);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q || searchKeys.length === 0) return data;
    return data.filter((row) =>
      searchKeys.some((k) => String(row[k] ?? "").toLowerCase().includes(q)),
    );
  }, [data, query, searchKeys]);

  const sorted = useMemo(() => {
    if (!sort) return filtered;
    const { key, dir } = sort;
    return [...filtered].sort((a, b) => {
      const av = a[key];
      const bv = b[key];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      if (typeof av === "number" && typeof bv === "number") {
        return dir === "asc" ? av - bv : bv - av;
      }
      const cmp = String(av).localeCompare(String(bv));
      return dir === "asc" ? cmp : -cmp;
    });
  }, [filtered, sort]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const safePage = Math.min(page, totalPages - 1);

  const pageData = useMemo(() => {
    const start = safePage * pageSize;
    return sorted.slice(start, start + pageSize);
  }, [sorted, safePage, pageSize]);

  const toggleSort = (key: keyof T) => {
    setPage(0);
    setSort((prev) => {
      if (!prev || prev.key !== key) return { key, dir: "asc" };
      return { key, dir: prev.dir === "asc" ? "desc" : "asc" };
    });
  };

  return {
    query,
    setQuery,
    page: safePage,
    setPage,
    sort,
    toggleSort,
    pageData,
    total: sorted.length,
    totalPages,
    pageSize,
  };
}
