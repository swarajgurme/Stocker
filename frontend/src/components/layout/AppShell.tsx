import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  Activity,
  Bell,
  Boxes,
  Gauge,
  LineChart as LineChartIcon,
  LogOut,
  Map,
  Menu,
  Moon,
  Settings,
  Sparkles,
  Sun,
  X,
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { useAuth } from "@/contexts/AuthContext";
import { useTheme } from "@/contexts/ThemeContext";
import { Button } from "@/components/ui/button";
import { canAccess, routeRoles } from "@/lib/roles";
import { cn } from "@/lib/utils";
import { BrandHeader, Logo } from "@/components/ui/Logo";
import { ChatbotWidget } from "@/components/chat/ChatbotWidget";

const nav = [
  { to: "/", label: "Executive", icon: Gauge, end: true, roles: routeRoles.executive },
  { to: "/forecast", label: "Forecasting", icon: LineChartIcon, roles: routeRoles.operations },
  { to: "/inventory", label: "Inventory", icon: Boxes, roles: routeRoles.operations },
  { to: "/analytics", label: "Analytics", icon: Map, roles: routeRoles.analytics },
  { to: "/anomalies", label: "Anomalies", icon: Bell, roles: routeRoles.anomalies },
  { to: "/recommendations", label: "AI Actions", icon: Sparkles, roles: routeRoles.operations },
  { to: "/reports", label: "Reports", icon: Activity, roles: routeRoles.reports },
  { to: "/settings", label: "Settings", icon: Settings, roles: routeRoles.settings },
] as const;

function NavItems({ onNavigate }: { onNavigate?: () => void }) {
  const { user } = useAuth();
  return (
    <>
      {nav
        .filter((item) => canAccess(user?.role, item.roles))
        .map((item) => {
          const { to, label, icon: Icon } = item;
          const end = "end" in item ? item.end : false;
          return (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={onNavigate}
              className={({ isActive }) =>
                cn(
                  "group relative flex items-center gap-3 rounded-[var(--radius)] px-3 py-2.5 text-sm font-medium transition-all duration-200",
                  isActive
                    ? "bg-[var(--accent)]/12 text-[var(--text)]"
                    : "text-[var(--muted)] hover:bg-[var(--surface-hover)] hover:text-[var(--text)]",
                )
              }
            >
              {({ isActive }) => (
                <>
                  {isActive ? (
                    <span className="absolute left-0 top-1/2 h-6 w-0.5 -translate-y-1/2 rounded-full bg-[var(--accent)]" />
                  ) : null}
                  <Icon
                    className={cn(
                      "h-4 w-4 shrink-0 transition-colors",
                      isActive ? "text-[var(--accent)]" : "text-[var(--muted)] group-hover:text-[var(--text)]",
                    )}
                  />
                  {label}
                </>
              )}
            </NavLink>
          );
        })}
    </>
  );
}

export function AppShell() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const location = useLocation();

  const roleLabel = user?.role?.replace(/_/g, " ") ?? "";

  return (
    <div className="flex min-h-screen">
      {/* Desktop sidebar */}
      <aside
        className="glass-panel-strong fixed inset-y-0 left-0 z-40 hidden w-[var(--sidebar-width)] flex-col border-r border-[var(--border)] md:flex"
        aria-label="Main navigation"
      >
        <div className="flex h-16 items-center border-b border-[var(--border)] px-5">
          <BrandHeader />
        </div>
        <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto p-3">
          <NavItems />
        </nav>
        <div className="px-3 pb-2">
          <button
            type="button"
            onClick={() => setChatOpen(true)}
            className="flex w-full items-center justify-between rounded-lg border border-emerald-500/25 bg-emerald-500/5 p-2.5 text-xs font-semibold text-[var(--text)] transition-all hover:border-emerald-500/45 hover:bg-emerald-500/10 group shadow-xs cursor-pointer"
          >
            <div className="flex items-center gap-2.5">
              <div className="flex h-7 w-7 items-center justify-center rounded-md bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 shadow-xs">
                <Sparkles className="h-3.5 w-3.5 animate-pulse" />
              </div>
              <div className="text-left">
                <div className="font-bold text-[11px] text-[var(--text)] font-mono">AI COPILOT</div>
                <div className="text-[10px] text-[var(--muted)] font-normal">Autonomous Intelligence</div>
              </div>
            </div>
            <span className="rounded bg-emerald-500/20 px-1.5 py-0.5 text-[9px] font-mono font-bold text-emerald-400">
              ACTIVE
            </span>
          </button>
        </div>
        <div className="border-t border-[var(--border)] p-4">
          <div className="rounded-[var(--radius)] bg-[var(--surface2)] p-3">
            <p className="truncate text-sm font-medium text-[var(--text)]">{user?.email}</p>
            <p className="truncate text-xs capitalize text-[var(--muted)]">{roleLabel}</p>
          </div>
          <div className="mt-2 flex gap-1">
            <Button
              variant="ghost"
              size="icon"
              type="button"
              onClick={toggleTheme}
              aria-label="Toggle theme"
            >
              {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="flex-1 justify-start text-[var(--muted)]"
              type="button"
              onClick={() => void logout()}
            >
              <LogOut className="mr-2 h-4 w-4" /> Sign out
            </Button>
          </div>
        </div>
      </aside>

      {/* Mobile drawer */}
      <AnimatePresence>
        {mobileOpen ? (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm md:hidden"
              onClick={() => setMobileOpen(false)}
            />
            <motion.aside
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", damping: 28, stiffness: 320 }}
              className="glass-panel-strong fixed inset-y-0 left-0 z-50 flex w-[min(85vw,280px)] flex-col border-r border-[var(--border)] md:hidden"
            >
              <div className="flex h-14 items-center justify-between border-b border-[var(--border)] px-4">
                <div className="flex items-center gap-2">
                  <Logo size={24} />
                  <span className="font-semibold text-sm">Stocker</span>
                </div>
                <Button variant="ghost" size="icon" type="button" onClick={() => setMobileOpen(false)}>
                  <X className="h-5 w-5" />
                </Button>
              </div>
              <nav className="flex flex-1 flex-col gap-0.5 p-3">
                <NavItems onNavigate={() => setMobileOpen(false)} />
              </nav>
            </motion.aside>
          </>
        ) : null}
      </AnimatePresence>

      <div className="flex min-h-screen flex-1 flex-col md:pl-[var(--sidebar-width)]">
        <header className="glass-panel sticky top-0 z-30 flex h-14 items-center justify-between gap-3 border-b border-[var(--border)] px-4 md:px-8">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden"
              type="button"
              onClick={() => setMobileOpen(true)}
              aria-label="Open menu"
            >
              <Menu className="h-5 w-5" />
            </Button>
            <span className="text-sm font-medium text-[var(--muted)] md:hidden">
              {nav.find((n) => location.pathname === n.to || (n.to !== "/" && location.pathname.startsWith(n.to)))?.label ?? "Stocker"}
            </span>
          </div>

          {/* Telemetry Status Bar & Desktop Copilot Launcher */}
          <div className="hidden md:flex items-center gap-3">
            <div className="flex items-center gap-2 rounded-md border border-[var(--border)] bg-[var(--surface2)] px-3 py-1 font-mono text-[11px] text-[var(--muted)]">
              <span className="flex h-2 w-2 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
              </span>
              <span className="text-[var(--text)] font-semibold">5 Store Nodes</span>
              <span className="text-[var(--border-strong)]">|</span>
              <span className="text-emerald-500 font-semibold">Telemetry Active</span>
              <span className="text-[var(--border-strong)]">|</span>
              <span>Prophet & Croston ML</span>
            </div>

            <button
              type="button"
              onClick={() => setChatOpen(true)}
              className="group flex items-center gap-2 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-400 hover:border-emerald-500/50 hover:bg-emerald-500/20 transition-all shadow-xs cursor-pointer"
            >
              <Sparkles className="h-3.5 w-3.5 text-emerald-400 animate-pulse" />
              <span>AI Copilot</span>
              <span className="rounded bg-emerald-500/20 px-1.5 py-0.2 text-[10px] text-emerald-300 font-mono font-bold">
                LIVE
              </span>
            </button>
          </div>

          <div className="flex items-center gap-2 md:hidden">
            <Button
              variant="ghost"
              size="sm"
              type="button"
              onClick={() => setChatOpen(true)}
              className="text-xs text-indigo-600 font-semibold flex items-center gap-1"
            >
              <Sparkles className="h-3.5 w-3.5" /> AI
            </Button>
            <Button variant="ghost" size="icon" type="button" onClick={toggleTheme}>
              {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </Button>
            <Button variant="outline" size="sm" type="button" onClick={() => void logout()}>
              Out
            </Button>
          </div>
        </header>

        <motion.main
          key={location.pathname}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
          className="flex-1 overflow-auto px-4 py-6 md:px-8 md:py-8"
        >
          <Outlet />
        </motion.main>
      </div>

      {/* Floating & Interactive Multilingual AI Assistant */}
      <ChatbotWidget isOpen={chatOpen} setIsOpen={setChatOpen} />
    </div>
  );
}
