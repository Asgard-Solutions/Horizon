import { AlertTriangle, Loader2 } from "lucide-react";
import type { ReactNode } from "react";

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div className="state" data-testid="loading-state">
      <Loader2 className="spin" size={36} />
      <span>{label}…</span>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="state state--error" role="alert" data-testid="error-state">
      <AlertTriangle size={36} />
      <span>{message}</span>
      {onRetry && (
        <button className="btn" onClick={onRetry} data-testid="error-retry-button">Try again</button>
      )}
    </div>
  );
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="empty" data-testid="empty-state">
      <h2>{title}</h2>
      {children}
    </div>
  );
}

export function PageHeader({ title, meta }: { title: string; meta?: ReactNode }) {
  return (
    <header className="page-head">
      <h1 data-testid="page-title">{title}</h1>
      {meta && <div className="page-meta">{meta}</div>}
    </header>
  );
}
