/** Mirrors backend `UserRole` string values */
export type UserRoleString =
  | "admin"
  | "business_analyst"
  | "supply_chain_planner"
  | "store_manager"
  | "executive";

/** Minimum role set per area (union of related API decorators). */
export const routeRoles = {
  executive: ["admin", "business_analyst", "executive"] as const,
  operations: [
    "admin",
    "business_analyst",
    "supply_chain_planner",
    "store_manager",
  ] as const,
  analytics: ["admin", "business_analyst", "executive"] as const,
  /** List + detect overlap for UX */
  anomalies: ["admin", "business_analyst", "executive", "supply_chain_planner"] as const,
  reports: ["admin", "business_analyst", "executive"] as const,
  /** Everyone authenticated */
  settings: [
    "admin",
    "business_analyst",
    "supply_chain_planner",
    "store_manager",
    "executive",
  ] as const,
} as const;

export function canAccess(
  role: string | null | undefined,
  allowed: readonly string[],
): boolean {
  if (!role) return false;
  return (allowed as readonly string[]).includes(role);
}
