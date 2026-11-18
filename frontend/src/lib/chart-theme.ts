/** Recharts styling aligned with Fleet & Autonomous Supply Chain Design Tokens */
export function chartTooltipStyle() {
  return {
    background: "var(--chart-tooltip-bg)",
    border: "1px solid var(--border-strong)",
    borderRadius: "8px",
    boxShadow: "var(--shadow-md)",
    fontSize: "12px",
    color: "var(--text)",
  } as const;
}

export const CHART_GRID = "var(--chart-grid)";
export const CHART_AXIS = "var(--muted)";
export const CHART_ACCENT = "var(--accent)";
export const CHART_CYAN = "var(--cyan)";
export const CHART_WARN = "var(--warn)";
export const CHART_VIOLET = "var(--violet)";
export const CHART_PALETTE = [
  "#10b981", // Alpine Emerald
  "#06b6d4", // Glacier Cyan
  "#f59e0b", // Solar Amber
  "#3b82f6", // Steel Blue
  "#14b8a6", // Teal Jade
  "#f43f5e", // Fleet Alert Rose
];
