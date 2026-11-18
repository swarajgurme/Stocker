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
          className="absolute inset-0 rounded-2xl bg-emerald-500/20 blur-md pointer-events-none"
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

          {/* Deep Spruce Left Face */}
          <linearGradient id="stocker-grad-left" x1="5" y1="16" x2="20" y2="35" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#059669" />
            <stop offset="100%" stopColor="#047857" />
          </linearGradient>

          {/* Glacier Cyan Right Face */}
          <linearGradient id="stocker-grad-right" x1="20" y1="16" x2="35" y2="35" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#06b6d4" />
            <stop offset="100%" stopColor="#0f766e" />
          </linearGradient>

          <filter id="stocker-shadow" x="-10%" y="-10%" width="120%" height="120%" filterUnits="userSpaceOnUse">
            <feDropShadow dx="0" dy="2" stdDeviation="2" floodColor="#022c22" floodOpacity="0.4" />
          </filter>
        </defs>

        {/* Outer Tactile Hexagonal Tile Container */}
        <rect
          width="40"
          height="40"
          rx="9"
          fill="url(#stocker-grad-left)"
          fillOpacity="0.14"
          stroke="rgba(52, 211, 153, 0.25)"
          strokeWidth="1"
        />

        {/* Isometric Stock Cube Top Face */}
        <path
          d="M20 7L32 13.8L20 20.6L8 13.8L20 7Z"
          fill="url(#stocker-grad-top)"
          filter="url(#stocker-shadow)"
        />

        {/* Isometric Stock Cube Left Face */}
        <path
          d="M7.5 15.5L19 22.1V34L7.5 27.4V15.5Z"
          fill="url(#stocker-grad-left)"
        />

        {/* Isometric Stock Cube Right Face */}
        <path
          d="M21 22.1L32.5 15.5V27.4L21 34V22.1Z"
          fill="url(#stocker-grad-right)"
        />

        {/* Autonomous Telemetry Pathway */}
        <path
          d="M13 13.5L20 9.5L27 13.5L20 17.5L13 13.5Z"
          fill="#ffffff"
          fillOpacity="0.4"
        />

        {/* Autonomous Central Node */}
        <circle cx="20" cy="20.5" r="2.5" fill="#ffffff" />
        <path
          d="M20 17V24M16.5 20.5H23.5"
          stroke="#ffffff"
          strokeWidth="1.2"
          strokeLinecap="round"
        />
      </svg>
    </div>
  );
}

export function BrandHeader({ className = "" }: { className?: string }) {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <Logo size={34} glow />
      <div>
        <div className="flex items-center gap-1.5">
          <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-[var(--accent)] font-mono">
            Stocker
          </p>
          <span className="rounded-[4px] bg-[var(--accent)]/15 px-1 py-0.2 text-[9px] font-mono text-[var(--accent)] border border-[var(--accent)]/30">
            FLEET
          </span>
        </div>
        <p className="text-sm font-semibold tracking-tight text-[var(--text)]">Autonomous SCM</p>
      </div>
    </div>
  );
}
