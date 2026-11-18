interface LogoProps {
  className?: string;
  size?: number | string;
  glow?: boolean;
}

export function Logo({ className = "", size = 32, glow = false }: LogoProps) {
  return (
    <div
      className={`relative inline-flex items-center justify-center shrink-0 ${className}`}
      style={{ width: size, height: size }}
    >
      {glow && (
        <div
          className="absolute inset-0 rounded-2xl bg-slate-300/20 blur-md pointer-events-none"
          style={{ transform: "scale(1.2)" }}
        />
      )}
      <svg
        width={size}
        height={size}
        viewBox="0 0 40 40"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="relative z-10 transition-transform duration-300 hover:scale-105"
      >
        <defs>
          {/* Alpine Emerald Top Face */}
          <linearGradient id="stocker-grad-top" x1="6" y1="5" x2="34" y2="21" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#34d399" />
            <stop offset="100%" stopColor="#10b981" />
          </linearGradient>

          {/* Liquid Brushed Silver Left Face */}
          <linearGradient id="stocker-grad-silver" x1="5" y1="16" x2="20" y2="35" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#ffffff" />
            <stop offset="35%" stopColor="#e2e8f0" />
            <stop offset="70%" stopColor="#94a3b8" />
            <stop offset="100%" stopColor="#64748b" />
          </linearGradient>

          {/* Deep Titanium Steel Right Face */}
          <linearGradient id="stocker-grad-titanium" x1="20" y1="16" x2="35" y2="35" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#475569" />
            <stop offset="60%" stopColor="#1e293b" />
            <stop offset="100%" stopColor="#0f172a" />
          </linearGradient>

          {/* Radiant Copper-Gold Node Gradient */}
          <linearGradient id="stocker-grad-copper" x1="16" y1="16" x2="24" y2="25" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#fffbeb" />
            <stop offset="30%" stopColor="#fcd34d" />
            <stop offset="65%" stopColor="#f59e0b" />
            <stop offset="100%" stopColor="#b45309" />
          </linearGradient>

          {/* Metallic Silver Rim Bevel */}
          <linearGradient id="stocker-silver-rim" x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#ffffff" stopOpacity="0.6" />
            <stop offset="50%" stopColor="#94a3b8" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#cbd5e1" stopOpacity="0.5" />
          </linearGradient>

          {/* Copper-Gold Edge Accent */}
          <linearGradient id="stocker-copper-rim" x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#fcd34d" stopOpacity="0.8" />
            <stop offset="50%" stopColor="#f59e0b" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#b45309" stopOpacity="0.7" />
          </linearGradient>

          <filter id="stocker-shadow" x="-10%" y="-10%" width="120%" height="120%" filterUnits="userSpaceOnUse">
            <feDropShadow dx="0" dy="2" stdDeviation="2" floodColor="#022c22" floodOpacity="0.45" />
          </filter>
        </defs>

        {/* Machined Metallic Base Tile */}
        <rect
          width="40"
          height="40"
          rx="9"
          fill="#0c1816"
          stroke="url(#stocker-silver-rim)"
          strokeWidth="1.2"
        />

        {/* Isometric Stock Cube Top Face (Alpine Emerald) */}
        <path
          d="M20 7L32 13.8L20 20.6L8 13.8L20 7Z"
          fill="url(#stocker-grad-top)"
          filter="url(#stocker-shadow)"
        />

        {/* Isometric Stock Cube Left Face (Brushed Metallic Silver) */}
        <path
          d="M7.5 15.5L19 22.1V34L7.5 27.4V15.5Z"
          fill="url(#stocker-grad-silver)"
          stroke="rgba(255, 255, 255, 0.4)"
          strokeWidth="0.5"
        />

        {/* Isometric Stock Cube Right Face (Deep Titanium Steel) */}
        <path
          d="M21 22.1L32.5 15.5V27.4L21 34V22.1Z"
          fill="url(#stocker-grad-titanium)"
          stroke="rgba(203, 213, 225, 0.2)"
          strokeWidth="0.5"
        />

        {/* Autonomous Telemetry Pathway with Silver Sheen */}
        <path
          d="M13 13.5L20 9.5L27 13.5L20 17.5L13 13.5Z"
          fill="#ffffff"
          fillOpacity="0.55"
        />

        {/* Autonomous Central Copper-Gold Node & Spark */}
        <circle cx="20" cy="20.5" r="3.2" fill="url(#stocker-grad-copper)" stroke="#fcd34d" strokeWidth="0.8" />
        <path
          d="M20 16.5V24.5M16 20.5H24"
          stroke="#fffbeb"
          strokeWidth="1.2"
          strokeLinecap="round"
        />
        <circle cx="20" cy="20.5" r="1" fill="#ffffff" />

        {/* Copper-Gold Machined Corner Beacon */}
        <path d="M34 5.5L38.5 10" stroke="#f59e0b" strokeWidth="1.4" strokeLinecap="round" />
      </svg>
    </div>
  );
}

export function BrandHeader({ className = "" }: { className?: string }) {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <Logo size={36} glow />
      <div>
        <div className="flex items-center gap-1.5 flex-wrap">
          <p className="text-[11px] font-bold uppercase tracking-[0.25em] font-mono silver-text">
            Stocker
          </p>
          <span className="silver-badge rounded-[4px] px-1 py-0.2 text-[8.5px] font-mono font-bold tracking-tight">
            SILVER
          </span>
          <span className="copper-gold-badge rounded-[4px] px-1 py-0.2 text-[8.5px] font-mono font-bold tracking-tight">
            COPPER-GOLD
          </span>
        </div>
        <p className="text-sm font-semibold tracking-tight text-[var(--text)]">Autonomous SCM</p>
      </div>
    </div>
  );
}
