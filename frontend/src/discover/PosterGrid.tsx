import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import type { BrowseItem } from "../types";
import { MediaCard } from "./MediaCard";

interface Props {
  total: number;
  get: (i: number) => BrowseItem | undefined;
  ensure: (from: number, to: number) => void;
  onOpen: (item: BrowseItem, index: number) => void;
  initialIndex: number | null;
  initialScroll: number | null;
  onFocusIndex: (i: number) => void;
  label: string;
}

const OVERSCAN = 3;
const reduced = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Virtualised poster wall: only rows near the screen exist in the DOM; arrows move by item/row deterministically. */
export function PosterGrid({ total, get, ensure, onOpen, initialIndex, initialScroll, onFocusIndex, label }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [cols, setCols] = useState(6);
  const [rowH, setRowH] = useState(420);
  const [range, setRange] = useState<[number, number]>([0, 4]);
  const [focusIdx, setFocusIdx] = useState<number | null>(initialIndex);
  const wantFocus = useRef(initialIndex !== null);
  const rows = Math.ceil(total / cols);

  const measure = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    const cs = getComputedStyle(el);
    const min = parseFloat(cs.getPropertyValue("--card-min")) || 190;
    const gap = parseFloat(cs.columnGap) || 24;
    const c = Math.max(2, Math.floor((el.clientWidth + gap) / (min + gap)));
    const cardW = (el.clientWidth - gap * (c - 1)) / c;
    setCols(c);
    setRowH(Math.round(cardW * 1.5 + parseFloat(cs.getPropertyValue("--label-h") || "86") + gap));
  }, []);

  const update = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const scale = r.width / (el.offsetWidth || 1) || 1; // same math with or without the 4K UI zoom
    const top = -r.top / scale;
    const first = Math.max(0, Math.floor(top / rowH) - OVERSCAN);
    const last = Math.min(rows - 1, Math.ceil((top + window.innerHeight / scale) / rowH) + OVERSCAN);
    setRange((p) => (p[0] === first && p[1] === last ? p : [first, last]));
  }, [rowH, rows]);

  useLayoutEffect(() => {
    measure();
    const ro = new ResizeObserver(measure);
    if (ref.current) ro.observe(ref.current);
    return () => ro.disconnect();
  }, [measure]);
  useEffect(() => {
    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => { window.removeEventListener("scroll", update); window.removeEventListener("resize", update); };
  }, [update]);
  useEffect(() => { ensure(range[0] * cols, (range[1] + 1) * cols - 1); }, [range, cols, ensure]);

  const reveal = useCallback((i: number, smooth: boolean) => {
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const scale = r.width / (el.offsetWidth || 1) || 1;
    const rowTop = (r.top / scale + Math.floor(i / cols) * rowH) * scale;
    const vh = window.innerHeight;
    if (rowTop < vh * 0.18 || rowTop + rowH * scale > vh * 0.96) {
      window.scrollTo({ top: window.scrollY + rowTop - vh * 0.3, behavior: smooth && !reduced() ? "smooth" : "auto" });
    }
  }, [cols, rowH]);

  useEffect(() => {
    if (initialIndex === null || !total) return;
    const i = Math.min(initialIndex, total - 1); // the title may have been removed: use the nearest remaining slot
    if (i !== focusIdx) setFocusIdx(i);
    if (initialScroll !== null) window.scrollTo({ top: initialScroll, behavior: "auto" });
    else reveal(i, false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [total > 0, cols]);

  useLayoutEffect(() => {
    if (focusIdx === null) return;
    const card = ref.current?.querySelector<HTMLElement>(`[data-index="${focusIdx}"]`);
    if (!card || document.activeElement === card) return;
    // Also re-focus when a loading placeholder that held focus was swapped for its real card.
    if (wantFocus.current || document.activeElement === document.body) {
      card.focus({ preventScroll: true });
      if (!card.classList.contains("dcard--loading")) wantFocus.current = false;
    }
  });

  const lastMove = useRef(0);
  const go = (i: number, repeat: boolean) => {
    const now = performance.now();
    const fast = repeat || now - lastMove.current < 180; // rapid input: jump instantly so focus never outruns rendering
    lastMove.current = now;
    const r = Math.floor(i / cols);
    setRange((p) => (r >= p[0] && r <= p[1] ? p : [Math.max(0, r - OVERSCAN), Math.min(rows - 1, r + OVERSCAN)]));
    wantFocus.current = true;
    setFocusIdx(i);
    reveal(i, !fast);
  };
  const onKeyDown = (e: React.KeyboardEvent) => {
    const i = Number((document.activeElement as HTMLElement)?.dataset.index);
    if (!Number.isInteger(i)) return;
    const col = i % cols;
    let next: number | null = null;
    if (e.key === "ArrowRight") next = col < cols - 1 && i + 1 < total ? i + 1 : i;
    else if (e.key === "ArrowLeft") next = col > 0 ? i - 1 : i;
    else if (e.key === "ArrowDown") next = i + cols < total ? i + cols : Math.floor(i / cols) < rows - 1 ? total - 1 : i;
    else if (e.key === "ArrowUp" && i - cols >= 0) next = i - cols;
    else return; // Up from the first row leaves the wall through normal spatial navigation
    e.preventDefault();
    if (next === i) {
      const el = document.activeElement as HTMLElement;
      el.classList.remove("nav-edge"); void el.offsetWidth; el.classList.add("nav-edge");
    } else go(next, e.repeat);
  };

  const cells = [];
  for (let r = range[0]; r <= range[1]; r++) {
    for (let c = 0; c < cols; c++) {
      const i = r * cols + c;
      if (i >= total) break;
      const item = get(i);
      const style = { top: r * rowH, left: `calc((100% - (var(--gap) * ${cols - 1})) / ${cols} * ${c} + var(--gap) * ${c})`,
        width: `calc((100% - (var(--gap) * ${cols - 1})) / ${cols})` };
      cells.push(item
        ? <div key={item.key} className="dgrid-cell" style={style} role="listitem">
            <MediaCard item={item} index={i} onOpen={() => onOpen(item, i)} onFocus={() => { setFocusIdx(i); onFocusIndex(i); }} />
          </div>
        : <div key={`ph-${i}`} className="dgrid-cell" style={style} role="listitem">
            <button className="dcard dcard--loading" data-index={i} aria-busy="true" aria-label="Loading" data-testid={`discover-card-loading-${i}`}>
              <span className="dcard-art" />
            </button>
          </div>);
    }
  }
  return (
    <div ref={ref} className="dgrid" role="list" aria-label={label} style={{ height: rows * rowH }} onKeyDown={onKeyDown}
      data-testid="discover-grid" data-cols={cols} data-total={total}>
      {cells}
    </div>
  );
}
