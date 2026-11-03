import type { AtlasData, AtlasNode } from "../types";

export const RADII = [0.17, 0.31, 0.46];
const CAPS: Record<string, number> = { types: 4, genres: 10, collections: 14 };
export const PAGE_RINGS = [8, 12, 16];
export const PAGE_SIZE = PAGE_RINGS.reduce((a, b) => a + b, 0);

/** Overview rings in a fixed order (Media, Genres, Collections); overflow folds into one "More" node per ring. */
export function overviewRings(data: AtlasData): AtlasNode[][] {
  return data.rings.filter((r) => r.nodes.length).map((r) => {
    const cap = CAPS[r.id] ?? 16;
    if (r.nodes.length <= cap) return r.nodes;
    const rest = r.nodes.slice(cap - 1);
    return [...r.nodes.slice(0, cap - 1), { id: `more:${r.id}`, kind: "more", value: r.id, label: `More ${r.label.toLowerCase()}`,
      count: rest.length, posters: [], children: rest }];
  });
}

/** Split one page of items over the three title orbits (8 / 12 / 16), inner first. */
export function pageRings<T>(items: T[]): T[][] {
  const out: T[][] = [];
  let i = 0;
  for (const n of PAGE_RINGS) {
    if (i >= items.length) break;
    out.push(items.slice(i, i + n));
    i += n;
  }
  return out;
}

// The inner ring starts at 9 o'clock so its few large nodes and labels sit clear of the genre ring.
/** Sparse group levels (e.g. "More genres") use the roomier outer orbits first so every name stays readable. */
export function groupRings<T>(items: T[]): { rings: T[][]; offset: number } {
  if (items.length <= 16) return { rings: items.length ? [items] : [], offset: 2 };
  if (items.length <= 28) return { rings: [items.slice(0, items.length - 16), items.slice(items.length - 16)], offset: 1 };
  return { rings: pageRings(items), offset: 0 };
}

export const angle = (i: number, n: number, ring: number) => -90 + (360 / n) * i + (ring === 0 ? -90 : ring * 22.5);

export function position(i: number, n: number, ring: number) {
  const a = (angle(i, n, ring) * Math.PI) / 180;
  const r = RADII[ring] ?? RADII[RADII.length - 1];
  return { x: 50 + Math.cos(a) * r * 100, y: 50 + Math.sin(a) * r * 100 };
}

const diff = (a: number, b: number) => Math.abs((((a - b) % 360) + 540) % 360 - 180);

/** Deterministic orbit navigation: Left/Right step around the ring, Up/Down jump to the nearest angle on the
 *  inner/outer ring. Returns null when the move leaves the Atlas (Up from the innermost ring). */
export function step(sizes: number[], ring: number, idx: number, key: string, off = 0): [number, number] | null | "stay" {
  const n = sizes[ring];
  if (key === "ArrowRight") return [ring, (idx + 1) % n];
  if (key === "ArrowLeft") return [ring, (idx - 1 + n) % n];
  const target = key === "ArrowUp" ? ring - 1 : key === "ArrowDown" ? ring + 1 : -2;
  if (target === -1) return null;
  if (target < 0 || target >= sizes.length) return "stay";
  const a = angle(idx, n, ring + off);
  let best = 0;
  for (let j = 1; j < sizes[target]; j++) if (diff(angle(j, sizes[target], target + off), a) < diff(angle(best, sizes[target], target + off), a)) best = j;
  return [target, best];
}
