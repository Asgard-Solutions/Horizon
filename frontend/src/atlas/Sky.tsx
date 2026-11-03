import { useLayoutEffect, useRef } from "react";
import { TitleArt } from "../components/TitleArt";
import { position, RADII, step } from "./layout";

export interface SkyNode {
  key: string;
  label: string;
  kind: string;
  count?: number;
  image?: string | null;
  state?: string;
  source?: string;
}

interface Props {
  rings: SkyNode[][];
  focus: [number, number];
  level: "overview" | "cluster";
  center: React.ReactNode;
  onFocus: (ring: number, idx: number) => void;
  onOpen: (ring: number, idx: number) => void;
  onExitUp: () => void;
  zoom: "in" | "out" | null;
}

const size = (count = 1) => Math.round(54 + Math.min(28, Math.log2(count + 1) * 6));

/** Fixed orbital rings; every node sits at a computed, stable angle. Keys are handled here so moves are exact. */
export function Sky({ rings, focus, level, center, onFocus, onOpen, onExitUp, zoom }: Props) {
  const box = useRef<HTMLDivElement>(null);
  const sizes = rings.map((r) => r.length);
  useLayoutEffect(() => {
    const el = box.current?.querySelector<HTMLElement>(`[data-ring="${focus[0]}"][data-idx="${focus[1]}"]`);
    if (el && box.current?.contains(document.activeElement) && document.activeElement !== el) el.focus({ preventScroll: true });
  }, [focus]);

  const onKeyDown = (e: React.KeyboardEvent) => {
    const t = e.target as HTMLElement;
    if (!t.dataset.ring || !e.key.startsWith("Arrow")) return;
    const next = step(sizes, Number(t.dataset.ring), Number(t.dataset.idx), e.key);
    e.preventDefault();
    if (next === null) onExitUp();
    else if (next !== "stay") onFocus(next[0], next[1]);
  };
  const p = position(focus[1], sizes[focus[0]] || 1, focus[0]);
  return (
    <div className={`sky sky--${level}${zoom ? ` sky--zoom-${zoom}` : ""}`} ref={box} onKeyDown={onKeyDown} data-testid={`atlas-sky-${level}`}
      style={{ "--px": `${(50 - p.x) * 0.06}%`, "--py": `${(50 - p.y) * 0.06}%` } as React.CSSProperties}>
      <div className="sky-plane">
        {rings.map((_, r) => (
          <span key={r} className={`orbit${focus[0] === r ? " orbit--active" : ""}`} style={{ "--r": RADII[r] } as React.CSSProperties} aria-hidden="true" />
        ))}
        <div className="sky-core" data-testid="atlas-core">{center}</div>
        {rings.map((ring, r) => ring.map((n, i) => {
          const pos = position(i, ring.length, r);
          const on = focus[0] === r && focus[1] === i;
          const px = level === "overview" ? size(n.count) : 58;
          return (
            <button key={n.key} className={`star star--${n.kind}${n.source ? ` star--${n.source}` : ""}${n.state ? ` star--${n.state}` : ""}${on ? " star--selected" : ""}`}
              style={{ left: `${pos.x}%`, top: `${pos.y}%`, "--s": `${px}px`, "--d": `${(r * 6 + i) * 18}ms` } as React.CSSProperties}
              data-ring={r} data-idx={i} aria-current={on ? "true" : undefined} data-autofocus={on || undefined}
              onFocus={() => !on && onFocus(r, i)} onClick={() => onOpen(r, i)} data-testid={`atlas-node-${n.key}`}
              aria-label={`${n.label}${n.count !== undefined ? `, ${n.count} title${n.count === 1 ? "" : "s"}` : ""}`}>
              <span className="star-body">
                {level === "cluster" && n.kind !== "group"
                  ? <TitleArt image={n.image ?? null} title={n.label} kind={n.kind} />
                  : <b className="star-count">{n.count}</b>}
              </span>
              {(level === "overview" || on) && <span className="star-label">{n.label}</span>}
            </button>
          );
        }))}
      </div>
    </div>
  );
}
