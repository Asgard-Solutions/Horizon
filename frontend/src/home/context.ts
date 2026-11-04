import type { ContinueItem } from "../types";

export type MediaType = "movie" | "tv";

export function parseMediaType(value: string | null): MediaType | null {
  return value === "movie" || value === "tv" ? value : null;
}

export function scopedPath(path: string, type: MediaType | null): string {
  if (!type) return path;
  const url = new URL(path, "http://horizon.local");
  url.searchParams.set("media", type);
  return url.pathname + url.search + url.hash;
}

export function continueItems(items: ContinueItem[], type: MediaType): ContinueItem[] {
  return items.filter(item => {
    const progress = item.progress;
    return item.type === (type === "movie" ? "movie" : "episode") && progress && !progress.watched
      && Number.isFinite(progress.position) && Number.isFinite(progress.duration)
      && progress.duration !== null && progress.duration > 0 && progress.position > 0 && progress.position < progress.duration;
  });
}

export function focusFallback(saved: string, ordinal: number, ids: string[], fallback: string): string {
  return ids.includes(saved) ? saved : ids[Math.max(0, Math.min(ordinal, ids.length - 1))] ?? fallback;
}

export const hubPath = (type: MediaType) => `/home/${type}`;

export interface HomeSpot {
  focusId: string;
  navigationId: string;
  resumeIndex: number;
  scrollLeft: number;
}

export function loadHomeSpot(type: MediaType | null): HomeSpot {
  const fallback = { focusId: type ? "hub-atlas" : "home-movies", navigationId: "hub-atlas", resumeIndex: 0, scrollLeft: 0 };
  try {
    const saved = JSON.parse(sessionStorage.getItem(`horizon.home.hub.${type ?? "selection"}`) ?? "null");
    if (!saved || typeof saved.focusId !== "string" || !/^(home-|hub-|resume-)[\w-]+$/.test(saved.focusId)) return fallback;
    return { focusId: saved.focusId, navigationId: /^hub-(atlas|discover|search)$/.test(saved.navigationId) ? saved.navigationId : "hub-atlas",
      resumeIndex: Number.isFinite(saved.resumeIndex) ? Math.max(0, saved.resumeIndex) : 0,
      scrollLeft: Number.isFinite(saved.scrollLeft) ? Math.max(0, saved.scrollLeft) : 0 };
  } catch { return fallback; }
}

export function saveHomeSpot(type: MediaType | null, spot: HomeSpot) {
  try { sessionStorage.setItem(`horizon.home.hub.${type ?? "selection"}`, JSON.stringify(spot)); } catch {}
}
