import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import { ThemeProvider } from "@/contexts/ThemeContext";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { routeRoles } from "@/lib/roles";
import { PageSkeleton } from "@/components/ui/skeleton";

const LoginPage = lazy(() => import("@/pages/LoginPage"));
const HomeEntry = lazy(() => import("@/pages/HomeEntry"));
const ForecastPage = lazy(() => import("@/pages/ForecastPage"));
const InventoryPage = lazy(() => import("@/pages/InventoryPage"));
const AnalyticsPage = lazy(() => import("@/pages/AnalyticsPage"));
const AnomaliesPage = lazy(() => import("@/pages/AnomaliesPage"));
const RecommendationsPage = lazy(() => import("@/pages/RecommendationsPage"));
const ReportsPage = lazy(() => import("@/pages/ReportsPage"));
const SettingsPage = lazy(() => import("@/pages/SettingsPage"));

function PageFallback() {
  return (
    <div className="mx-auto max-w-6xl p-4 md:p-0">
      <PageSkeleton />
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <Suspense fallback={<PageFallback />}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<ProtectedRoute />}>
              <Route index element={<HomeEntry />} />
              <Route
                path="forecast"
                element={
                  <RoleGuard allow={routeRoles.operations}>
                    <ForecastPage />
                  </RoleGuard>
                }
              />
              <Route
                path="inventory"
                element={
                  <RoleGuard allow={routeRoles.operations}>
                    <InventoryPage />
                  </RoleGuard>
                }
              />
              <Route
                path="analytics"
                element={
                  <RoleGuard allow={routeRoles.analytics}>
                    <AnalyticsPage />
                  </RoleGuard>
                }
              />
              <Route
                path="anomalies"
                element={
                  <RoleGuard allow={routeRoles.anomalies}>
                    <AnomaliesPage />
                  </RoleGuard>
                }
              />
              <Route
                path="recommendations"
                element={
                  <RoleGuard allow={routeRoles.operations}>
                    <RecommendationsPage />
                  </RoleGuard>
                }
              />
              <Route
                path="reports"
                element={
                  <RoleGuard allow={routeRoles.reports}>
                    <ReportsPage />
                  </RoleGuard>
                }
              />
              <Route
                path="settings"
                element={
                  <RoleGuard allow={routeRoles.settings}>
                    <SettingsPage />
                  </RoleGuard>
                }
              />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          </Suspense>
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}
