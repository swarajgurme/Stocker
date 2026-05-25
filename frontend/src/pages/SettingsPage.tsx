import { Moon, Server, Shield, Sun } from "lucide-react";
import { useTheme } from "@/contexts/ThemeContext";
import { useAuth } from "@/contexts/AuthContext";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const { user } = useAuth();

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <PageHeader
        title="Workspace settings"
        description="Appearance, API connectivity, and security preferences."
      />

      <Card glow>
        <CardHeader className="flex flex-row items-center gap-3">
          {theme === "dark" ? <Moon className="h-5 w-5 text-[var(--accent)]" /> : <Sun className="h-5 w-5 text-[var(--accent)]" />}
          <CardTitle>Appearance</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button
            variant={theme === "dark" ? "primary" : "outline"}
            size="sm"
            type="button"
            onClick={() => setTheme("dark")}
          >
            Dark
          </Button>
          <Button
            variant={theme === "light" ? "primary" : "outline"}
            size="sm"
            type="button"
            onClick={() => setTheme("light")}
          >
            Light
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center gap-3">
          <Server className="h-5 w-5 text-[var(--accent)]" />
          <CardTitle>API & environment</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-[var(--text-secondary)]">
          <p>
            Requests use the Vite dev proxy at{" "}
            <code className="rounded bg-[var(--surface2)] px-1.5 py-0.5 text-xs text-[var(--accent)]">/api</code>{" "}
            or <code className="rounded bg-[var(--surface2)] px-1.5 py-0.5 text-xs">VITE_API_URL</code> when set.
          </p>
          <div className="flex flex-wrap gap-2">
            <Badge tone="muted">Role: {user?.role?.replace(/_/g, " ")}</Badge>
            <Badge tone="muted">{user?.email}</Badge>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center gap-3">
          <Shield className="h-5 w-5 text-[var(--accent)]" />
          <CardTitle>Security</CardTitle>
        </CardHeader>
        <CardContent className="text-sm leading-relaxed text-[var(--text-secondary)]">
          <p>
            Authentication uses rotating JWT access and refresh tokens. Logout blacklists active
            tokens server-side. For production clusters, configure Redis-backed denylist and HTTPS.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
