import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ErrorBoundary } from "react-error-boundary";
import App from "@/App";
import "./index.css";

function Fallback({ error }: { error: Error }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-2 p-6 text-center">
      <h1 className="text-lg font-semibold text-[var(--danger)]">
        Application error
      </h1>
      <pre className="max-w-xl overflow-auto rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4 text-left text-xs text-[var(--muted)]">
        {error.message}
      </pre>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary FallbackComponent={Fallback}>
      <App />
    </ErrorBoundary>
  </StrictMode>,
);
