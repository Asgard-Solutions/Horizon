import type { Compatibility } from "../types";

const LABEL: Record<Compatibility["status"], string> = {
  supported: "Plays in browser",
  maybe: "May not play in every browser",
  unsupported: "Not playable in browser",
  unknown: "Compatibility not checked",
};

export function CompatBadge({ compat }: { compat: Compatibility }) {
  return (
    <div className={`compat compat--${compat.status}`} data-testid="compat-badge">
      <strong data-testid="compat-status">{LABEL[compat.status]}</strong>
      {compat.reasons.length > 0 && (
        <ul data-testid="compat-reasons">
          {compat.reasons.map((r) => <li key={r}>{r}</li>)}
        </ul>
      )}
    </div>
  );
}
