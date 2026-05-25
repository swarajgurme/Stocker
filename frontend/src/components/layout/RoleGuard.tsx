import type { ReactElement } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/contexts/AuthContext";

export function RoleGuard({
  allow,
  children,
}: {
  allow: readonly string[];
  children: ReactElement;
}) {
  const { user } = useAuth();
  const role = user?.role;
  if (!role || !allow.includes(role)) {
    return (
      <div className="mx-auto max-w-lg py-12">
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardHeader>
            <CardTitle className="text-amber-100">Insufficient permissions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-[var(--muted)]">
            <p>
              Your role ({role ?? "unknown"}) cannot access this module. Contact an
              administrator if you need access.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }
  return children;
}
