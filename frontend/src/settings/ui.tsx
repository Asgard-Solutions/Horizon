import type { ReactNode } from "react";

/** One setting: label + explanation on the left, its control on the right. */
export function SettingRow({ label, hint, children, testId }: { label: string; hint?: ReactNode; children: ReactNode; testId: string }) {
  return (
    <div className="srow" data-testid={testId}>
      <div className="srow-text">
        <strong>{label}</strong>
        {hint && <span>{hint}</span>}
      </div>
      <div className="srow-control">{children}</div>
    </div>
  );
}

/** Segmented choice: the current value is the highlighted pill (aria-pressed). Left/Right stay inside the row. */
export function Choice<T extends string | number>({ value, options, onChange, testId, disabled }: {
  value: T; options: { value: T; label: string }[]; onChange: (v: T) => void; testId: string; disabled?: boolean;
}) {
  return (
    <div className="schoice" role="group" data-nav-row data-testid={testId}>
      {options.map((o) => (
        <button key={String(o.value)} type="button" className="schoice-opt" aria-pressed={o.value === value} disabled={disabled}
          onClick={() => onChange(o.value)} data-testid={`${testId}-${o.value}`}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Toggle({ on, onChange, testId, labels = ["Off", "On"] }: { on: boolean; onChange: (v: boolean) => void; testId: string; labels?: [string, string] }) {
  return (
    <button type="button" className="stoggle" role="switch" aria-checked={on} onClick={() => onChange(!on)} data-testid={testId}>
      <span className="stoggle-track"><span /></span>{on ? labels[1] : labels[0]}
    </button>
  );
}

/** Honest placeholder for options that do not work yet. Not focusable, never looks like a control. */
export function ComingLater({ label, hint, testId }: { label: string; hint: string; testId: string }) {
  return (
    <div className="srow srow--later" data-testid={testId}>
      <div className="srow-text"><strong>{label}</strong><span>{hint}</span></div>
      <span className="sbadge">Coming later</span>
    </div>
  );
}

export function SectionHead({ title, intro }: { title: string; intro?: ReactNode }) {
  return (
    <header className="ssection-head">
      <h2>{title}</h2>
      {intro && <p>{intro}</p>}
    </header>
  );
}

export const fmtBytes = (n: number) => {
  const u = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return `${n >= 10 || i === 0 ? Math.round(n) : n.toFixed(1)} ${u[i]}`;
};
export const fmtWhen = (iso: string | null | undefined) => (iso ? new Date(iso).toLocaleString([], { dateStyle: "medium", timeStyle: "short" }) : "Never");
