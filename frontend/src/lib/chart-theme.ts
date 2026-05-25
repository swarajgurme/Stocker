/** Recharts styling aligned with CSS design tokens */
export function chartTooltipStyle() {
  return {
    background: "var(--chart-tooltip-bg)",
    border: "1px solid var(--border-strong)",
    borderRadius: "10px",
    boxShadow: "var(--shadow-md)",
    fontSize: "12px",
    color: "var(--text)",
  } as const;
}

export const CHART_GRID = "var(--chart-grid)";
export const CHART_AXIS = "var(--muted)";
export const CHART_ACCENT = "var(--accent)";
export const CHART_VIOLET = "var(--violet)";
export const CHART_WARN = "var(--warn)";
export const CHART_PALETTE = [
  "#2dd4bf",
  "#818cf8",
  "#f59e0b",
  "#ec4899",
  "#22c55e",
  "#38bdf8",
];
