import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Logo } from "@/components/ui/Logo";

interface SplashTransitionProps {
  onComplete?: () => void;
  force?: boolean;
}

export function SplashTransition({ onComplete, force = false }: SplashTransitionProps) {
  const [visible, setVisible] = useState(() => {
    if (force) return true;
    const shown = sessionStorage.getItem("stocker_splash_shown");
    return !shown;
  });

  useEffect(() => {
    if (!visible) {
      onComplete?.();
      return;
    }

    // Play splash sequence: holds center stage, then slowly fades
    const timer = setTimeout(() => {
      setVisible(false);
      sessionStorage.setItem("stocker_splash_shown", "true");
    }, 2200);

    return () => clearTimeout(timer);
  }, [visible, onComplete]);

  return (
    <AnimatePresence onExitComplete={onComplete}>
      {visible && (
        <motion.div
          key="stocker-splash-overlay"
          initial={{ opacity: 1 }}
          animate={{ opacity: 1 }}
          exit={{
            opacity: 0,
            scale: 1.04,
            filter: "blur(12px)",
            transition: { duration: 0.9, ease: [0.22, 1, 0.36, 1] },
          }}
          className="fixed inset-0 z-[9999] flex flex-col items-center justify-center bg-[var(--bg)] select-none overflow-hidden"
          style={{
            background:
              "radial-gradient(ellipse 80% 60% at 50% 45%, rgba(16, 185, 129, 0.16), transparent 65%), radial-gradient(ellipse 50% 35% at 50% 60%, rgba(245, 158, 11, 0.08), transparent 70%), var(--bg)",
          }}
        >
          {/* Subtle Industrial Grid Background Pattern */}
          <div
            className="pointer-events-none absolute inset-0 opacity-25"
            style={{
              backgroundImage:
                "linear-gradient(to right, rgba(110, 231, 183, 0.06) 1px, transparent 1px), linear-gradient(to bottom, rgba(110, 231, 183, 0.06) 1px, transparent 1px)",
              backgroundSize: "48px 48px",
            }}
          />

          {/* Ambient Radial Flare */}
          <div className="absolute h-96 w-96 rounded-full bg-emerald-500/10 blur-[120px] pointer-events-none" />

          {/* Center Stage Card & Content */}
          <motion.div
            initial={{ opacity: 0, y: 18, scale: 0.94 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
            className="relative z-10 flex flex-col items-center text-center px-6"
          >
            {/* Glowing Stocker 3D Logo */}
            <motion.div
              animate={{
                y: [0, -5, 0],
              }}
              transition={{
                duration: 3,
                repeat: Infinity,
                ease: "easeInOut",
              }}
              className="relative mb-6"
            >
              <div className="absolute inset-0 rounded-2xl bg-gradient-to-tr from-emerald-500/30 to-amber-500/20 blur-xl scale-125 pointer-events-none" />
              <Logo size={76} glow />
            </motion.div>

            {/* Brand Title: STOCKER in Center */}
            <motion.h1
              initial={{ opacity: 0, letterSpacing: "0.2em" }}
              animate={{ opacity: 1, letterSpacing: "0.38em" }}
              transition={{ duration: 0.85, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
              className="text-3xl md:text-4xl font-extrabold uppercase font-mono silver-text tracking-[0.38em] pl-[0.38em] drop-shadow-md"
            >
              STOCKER
            </motion.h1>

            {/* One Line Underneath */}
            <motion.p
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.35, ease: [0.16, 1, 0.3, 1] }}
              className="mt-3 max-w-md text-xs md:text-sm font-medium tracking-[0.2em] uppercase text-[var(--muted)]"
            >
              Autonomous Supply Chain & Multi-Store Inventory Intelligence
            </motion.p>

            {/* Machined Precision Progress Telemetry Line */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.5 }}
              className="mt-8 flex flex-col items-center gap-2"
            >
              <div className="relative h-[2px] w-52 md:w-64 rounded-full bg-slate-800/80 overflow-hidden silver-rim">
                <motion.div
                  initial={{ width: "0%" }}
                  animate={{ width: "100%" }}
                  transition={{ duration: 1.5, delay: 0.35, ease: [0.22, 1, 0.36, 1] }}
                  className="h-full bg-gradient-to-r from-emerald-500 via-teal-400 to-amber-400 shadow-[0_0_10px_rgba(16,185,129,0.8)]"
                />
              </div>

              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: [0, 0.85, 0.5] }}
                transition={{ duration: 1.2, delay: 0.6 }}
                className="text-[10px] font-mono tracking-widest text-emerald-400/80 uppercase"
              >
                Initializing Autonomous Network
              </motion.span>
            </motion.div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
