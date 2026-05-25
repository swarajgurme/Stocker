import { useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Lock, Mail, Sparkles, User } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { useTheme } from "@/contexts/ThemeContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert } from "@/components/ui/alert";
import { Label } from "@/components/ui/label";

export default function LoginPage() {
  const { login, register, isAuthenticated } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password, name);
    } catch (err: unknown) {
      setError((err as Error).message ?? "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden p-4">
      <div
        className="pointer-events-none absolute inset-0 opacity-60"
        aria-hidden
        style={{
          background:
            "radial-gradient(ellipse 80% 50% at 50% -20%, var(--accent-glow), transparent), radial-gradient(ellipse 40% 30% at 100% 50%, rgba(129,140,248,0.12), transparent)",
        }}
      />
      <div className="absolute right-4 top-4">
        <Button variant="ghost" size="sm" type="button" onClick={toggleTheme}>
          {theme === "dark" ? "Light mode" : "Dark mode"}
        </Button>
      </div>
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
        className="relative w-full max-w-md"
      >
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-[var(--accent)] to-[var(--violet)] shadow-[var(--shadow-glow)]">
            <Sparkles className="h-7 w-7 text-[var(--accent-foreground)]" />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">
            <span className="gradient-text">Stocker Enterprise</span>
          </h1>
          <p className="mt-2 text-sm text-[var(--muted)]">
            AI supply chain intelligence for modern operations
          </p>
        </div>
        <Card className="gradient-border" glow>
          <CardHeader className="border-0 pb-0">
            <CardTitle className="text-center text-base">Secure access</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="mb-5 flex rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface2)] p-1">
              {(["login", "register"] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  className={`flex-1 rounded-md py-2 text-sm font-medium transition ${
                    mode === m
                      ? "bg-[var(--bg-elevated)] text-[var(--text)] shadow-sm"
                      : "text-[var(--muted)] hover:text-[var(--text)]"
                  }`}
                  onClick={() => setMode(m)}
                >
                  {m === "login" ? "Sign in" : "Register"}
                </button>
              ))}
            </div>
            <form className="space-y-4" onSubmit={(e) => void submit(e)}>
              {mode === "register" ? (
                <Label>
                  Full name
                  <div className="relative mt-1">
                    <User className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--muted)]" />
                    <Input
                      className="pl-9"
                      placeholder="Your name"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                    />
                  </div>
                </Label>
              ) : null}
              <Label>
                Email
                <div className="relative mt-1">
                  <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--muted)]" />
                  <Input
                    className="pl-9"
                    type="email"
                    placeholder="you@company.com"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>
              </Label>
              <Label>
                Password
                <div className="relative mt-1">
                  <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--muted)]" />
                  <Input
                    className="pl-9"
                    type="password"
                    placeholder="Min. 8 characters"
                    required
                    minLength={8}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </div>
              </Label>
              {error ? <Alert variant="error">{error}</Alert> : null}
              <Button type="submit" className="w-full" size="lg" disabled={loading}>
                {loading ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
              </Button>
            </form>
            <p className="mt-5 text-center text-[11px] leading-relaxed text-[var(--muted)]">
              Demo: analyst@stocker.demo · DemoPass123!
            </p>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
