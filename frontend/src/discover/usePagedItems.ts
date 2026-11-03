import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { BrowseItem, DiscoverPage } from "../types";

const PAGE = 120;

/** Loads a Discover result in pages on demand, so large libraries never send or render everything at once. */
export function usePagedItems(query: string) {
  const pages = useRef(new Map<number, BrowseItem[]>());
  const pending = useRef(new Set<number>());
  const [cur, setCur] = useState<{ q: string; d: DiscoverPage } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [, setTick] = useState(0);
  const seq = useRef(0);

  // The previous result (and its facets) stays available while the next one loads, so filter controls never unmount mid-use.
  useEffect(() => {
    const n = ++seq.current;
    pages.current = new Map();
    pending.current = new Set();
    setError(null);
    api<DiscoverPage>(`/api/discover?${query}${query ? "&" : ""}offset=0&limit=${PAGE}`)
      .then((d) => { if (n === seq.current) { pages.current.set(0, d.items); setCur({ q: query, d }); } })
      .catch((e: Error) => n === seq.current && setError(e.message));
  }, [query]);

  const ensure = useCallback((from: number, to: number) => {
    for (let p = Math.floor(Math.max(0, from) / PAGE); p <= Math.floor(Math.max(0, to) / PAGE); p++) {
      if (pages.current.has(p) || pending.current.has(p)) continue;
      pending.current.add(p);
      const n = seq.current;
      api<DiscoverPage>(`/api/discover?${query}${query ? "&" : ""}offset=${p * PAGE}&limit=${PAGE}`)
        .then((d) => { if (n === seq.current) { pages.current.set(p, d.items); setTick((t) => t + 1); } })
        .finally(() => pending.current.delete(p));
    }
  }, [query]);

  const get = useCallback((i: number) => pages.current.get(Math.floor(i / PAGE))?.[i % PAGE], []);
  const first = cur && cur.q === query ? cur.d : null;
  return { first, error, total: first?.total ?? 0, facets: cur?.d.facets ?? null, get, ensure };
}
