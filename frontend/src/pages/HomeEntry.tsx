import { lazy, Suspense } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { canAccess, routeRoles } from "@/lib/roles";
import { Spinner } from "@/components/ui/spinner";

const DashboardPage = lazy(() => import("@/pages/DashboardPage"));

/**
 * Default landing: executive KPIs when permitted, otherwise operations workbench.
 */
export default function HomeEntry() {
  const { user } = useAuth();
  const role = user?.role;

  if (canAccess(role, routeRoles.executive)) {
    return (
      <Suspense
        fallback={
          <div className="flex justify-center py-20">
            <Spinner className="h-10 w-10" />
          </div>
        }
      >
        <DashboardPage />
      </Suspense>
    );
  }

  if (canAccess(role, routeRoles.operations)) {
    return <Navigate to="/forecast" replace />;
  }

  return <Navigate to="/settings" replace />;
}
