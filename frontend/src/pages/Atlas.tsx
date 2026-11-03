import { ArrowLeft, ChevronLeft, ChevronRight, LayoutGrid, Orbit } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { pageRings, PAGE_SIZE, overviewRings } from "../atlas/layout";
import { InfoPanel } from "../atlas/InfoPanel";
import { Sky, type SkyNode } from "../atlas/Sky";
import { ErrorState, Loading } from "../components/States";
import { MediaCard } from "../discover/MediaCard";
import { detailPath } from "../discover/query";
import { useAsync, useBack } from "../hooks";
import type { AtlasData, AtlasNode, DiscoverPage, MediaItem } from "../types";

type Level = { node: AtlasNode | null; page: number; focus: [number, number] };
const STACK_KEY = "horizon.atlas.stack";
const MODE_KEY = "horizon.atlas.mode";
const loadStack = (): Level[] => { try { const s = JSON.parse(sessionStorage.getItem(STACK_KEY) ?? "null"); return Array.isArray(s) && s.length ? s : [{ node: null, page: 0, focus: [0, 0] }]; } catch { return [{ node: null, page: 0, focus: [0, 0] }]; } };

function nodeQuery(n: AtlasNode): string {
  if (n.kind === "type") return `view=${n.value === "movie" ? "movies" : "shows"}`;
  if (n.kind === "genre") return `genre=${encodeURIComponent(String(n.value))}`;
  return `collection=${n.value}`;
}
const toSky = (n: AtlasNode): SkyNode => ({ key: n.id, label: n.label, kind: n.kind === "more" ? "more" : n.kind, count: n.count, source: n.source });
const itemSky = (m: MediaItem): SkyNode => ({ key: m.key, label: m.title, kind: m.type, image: m.poster_url, state: m.state });

export default function Atlas() {
  const navigate = useNavigate();
  const { data, error, reload } = useAsync(() => api<AtlasData>("/api/atlas"), []);
  const [stack, setStack] = useState<Level[]>(loadStack);
  const [mode, setMode] = useState<"orbit" | "grid">(() => (localStorage.getItem(MODE_KEY) === "grid" ? "grid" : "orbit"));
  const [zoom, setZoom] = useState<"in" | "out" | null>(null);
  const [page, setPage] = useState<{ key: string; items: MediaItem[]; total: number } | null>(null);
  const toolbar = useRef<HTMLDivElement>(null);
  const level = stack[stack.length - 1];
  const node = level.node;
  useEffect(() => sessionStorage.setItem(STACK_KEY, JSON.stringify(stack)), [stack]);

  const pageKey = node && node.kind !== "more" ? `${nodeQuery(node)}&p=${level.page}` : null;
  useEffect(() => {
    if (!node || node.kind === "more") return;
    const key = `${nodeQuery(node)}&p=${level.page}`;
    api<DiscoverPage>(`/api/discover?${nodeQuery(node)}&sort=title&offset=${level.page * PAGE_SIZE}&limit=${PAGE_SIZE}`)
      .then((d) => setPage({ key, items: d.items as MediaItem[], total: d.total }));
  }, [node, level.page]);

  const overview = useMemo(() => (data ? overviewRings(data) : []), [data]);
  const groupItems = node?.kind === "more" ? (node.children ?? []).slice(level.page * PAGE_SIZE, (level.page + 1) * PAGE_SIZE) : null;
  const titles = page && page.key === pageKey ? page.items : null;
  const total = node ? (node.kind === "more" ? node.children?.length ?? 0 : page?.total ?? node.count) : data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const rings: SkyNode[][] = !node ? overview.map((r) => r.map(toSky))
    : groupItems ? pageRings(groupItems.map(toSky)) : titles ? pageRings(titles.map(itemSky)) : [];
  const flat = !node ? overview.flat() : groupItems ?? titles ?? [];
  const focusIdx = rings.slice(0, level.focus[0]).reduce((a, r) => a + r.length, 0) + level.focus[1];
  const focused = rings[level.focus[0]]?.[level.focus[1]] ? flat[focusIdx] : undefined;

  const patch = useCallback((p: Partial<Level>) => setStack((s) => [...s.slice(0, -1), { ...s[s.length - 1], ...p }]), []);
  // Restored levels may point at titles or groups that were removed since: fall back to the nearest valid spot.
  const ready = !node || !!groupItems || !!titles;
  useEffect(() => {
    if (!data || !ready) return;
    if (node && !rings.length) {
      if (level.page > 0) patch({ page: pages - 1, focus: [0, 0] });
      else setStack((s) => (s.length > 1 ? s.slice(0, -1) : s));
      return;
    }
    if (!rings.length || rings[level.focus[0]]?.[level.focus[1]]) return;
    const r = Math.min(level.focus[0], rings.length - 1);
    patch({ focus: [r, Math.min(level.focus[1], rings[r].length - 1)] });
  });
  const focusSelected = () => {
    let tries = 0;
    const t = window.setInterval(() => { // the next level may still be loading its titles
      const hit = document.querySelector<HTMLElement>(".atlas [aria-current='true']");
      const el = hit && !hit.matches("button") ? hit.querySelector<HTMLElement>("button") : hit;
      if (el) el.focus({ preventScroll: true });
      if (el || ++tries > 40) window.clearInterval(t);
    }, 50);
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => focusSelected(), []); // returning from a title lands on that exact title in orbit or grid mode
  const openAt = (r: number, i: number) => {
    const idx = rings.slice(0, r).reduce((a, x) => a + x.length, 0) + i;
    const target = flat[idx];
    if (!target) return;
    patch({ focus: [r, i] });
    if ("type" in target && (target.type === "movie" || target.type === "show")) { navigate(detailPath(target)); return; }
    setZoom("in");
    setStack((s) => [...s.slice(0, -1), { ...s[s.length - 1], focus: [r, i] }, { node: target as AtlasNode, page: 0, focus: [0, 0] }]);
    focusSelected();
  };
  const setPageTo = (p: number) => { if (p >= 0 && p < pages) { patch({ page: p, focus: [0, 0] }); focusSelected(); } };
  useBack(() => {
    if (stack.length < 2) return false;
    setZoom("out");
    setStack((s) => s.slice(0, -1));
    focusSelected();
    return true;
  });
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!node || e.defaultPrevented || (e.key !== "PageUp" && e.key !== "PageDown")) return;
      e.preventDefault();
      setPageTo(level.page + (e.key === "PageDown" ? 1 : -1));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });
  const toggleMode = () => { const m = mode === "orbit" ? "grid" : "orbit"; setMode(m); localStorage.setItem(MODE_KEY, m); focusSelected(); };

  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return <Loading />;
  if (!data.total) return (
    <div className="page atlas-empty" data-testid="atlas-empty"><h1>Your Atlas is waiting</h1>
      <p>Add a media folder and your movies and series will appear here as a map of genres and collections.</p>
      <button className="hbtn hbtn--primary" data-autofocus onClick={() => navigate("/settings")} data-testid="atlas-add-folder">Add media folder</button></div>
  );
  const crumb = node ? node.label : "Your library";
  return (
    <div className={`atlas atlas--${mode}`} data-testid="atlas-page" data-level={node ? "cluster" : "overview"}>
      <div className="atlas-toolbar" ref={toolbar} data-nav-row data-testid="atlas-toolbar">
        {node && <button className="hbtn hbtn--quiet" onClick={() => { setZoom("out"); setStack((s) => s.slice(0, -1)); focusSelected(); }} data-testid="atlas-back"><ArrowLeft size={20} /> Back</button>}
        <h1 className="atlas-crumb" data-testid="atlas-crumb">{crumb}<span>{total} {node?.kind === "more" ? "groups" : total === 1 ? "title" : "titles"}</span></h1>
        {node && pages > 1 && (
          <span className="atlas-pager" data-testid="atlas-pager">
            <button className="hbtn hbtn--quiet" disabled={level.page === 0} onClick={() => setPageTo(level.page - 1)} aria-label="Previous page" data-testid="atlas-prev-page"><ChevronLeft size={20} /></button>
            <span data-testid="atlas-page-label">{level.page + 1} / {pages}</span>
            <button className="hbtn hbtn--quiet" disabled={level.page >= pages - 1} onClick={() => setPageTo(level.page + 1)} aria-label="Next page" data-testid="atlas-next-page"><ChevronRight size={20} /></button>
          </span>
        )}
        <button className="hbtn hbtn--quiet atlas-mode" onClick={toggleMode} data-testid="atlas-mode-toggle">
          {mode === "orbit" ? <><LayoutGrid size={20} /> Grid view</> : <><Orbit size={20} /> Orbit view</>}</button>
      </div>
      {data.sources.unreachable > 0 && <p className="atlas-banner" data-testid="atlas-unreachable">{data.sources.unreachable} media folder{data.sources.unreachable === 1 ? " is" : "s are"} unavailable. Its titles are still listed.</p>}
      <div className="atlas-body">
        <InfoPanel node={focused} level={node ? "cluster" : "overview"} />
        {node && !groupItems && !titles ? <Loading /> : mode === "orbit" ? (
          <Sky key={`${node?.id ?? "root"}-${level.page}`} rings={rings} focus={level.focus} level={node ? "cluster" : "overview"} zoom={zoom}
            onFocus={(r, i) => patch({ focus: [r, i] })} onOpen={openAt}
            onExitUp={() => toolbar.current?.querySelector<HTMLElement>("button:not([disabled]):not([hidden])")?.focus()}
            center={<><b>{crumb}</b><span>{total}</span></>} />
        ) : (
          <div className="atlas-grid" role="list" data-testid="atlas-grid">
            {rings.map((ring, r) => ring.map((n, i) => {
              const idx = rings.slice(0, r).reduce((a, x) => a + x.length, 0) + i;
              const item = flat[idx];
              const on = level.focus[0] === r && level.focus[1] === i;
              return item && "type" in item ? (
                <div role="listitem" key={n.key} aria-current={on ? "true" : undefined}>
                  <MediaCard item={item} index={idx} onOpen={() => openAt(r, i)} onFocus={() => patch({ focus: [r, i] })} />
                </div>
              ) : (
                <button key={n.key} role="listitem" className={`atlas-gcard star--${n.kind}${n.source ? ` star--${n.source}` : ""}`} aria-current={on ? "true" : undefined}
                  data-autofocus={on || undefined} onFocus={() => patch({ focus: [r, i] })} onClick={() => openAt(r, i)} data-testid={`atlas-gnode-${n.key}`}>
                  <b>{n.label}</b><span>{n.count} {n.kind === "more" ? "groups" : "titles"}</span>
                </button>
              );
            }))}
          </div>
        )}
      </div>
      <p className="atlas-hints" aria-hidden="true">{mode === "orbit" ? <><kbd>◀ ▶</kbd> around the orbit · <kbd>▲ ▼</kbd> between orbits</> : <><kbd>◀ ▶ ▲ ▼</kbd> move</>} · <kbd>A</kbd> {node ? "open" : "explore"} · <kbd>B</kbd> {node ? "zoom out" : "back"}{node && pages > 1 ? " · LB / RB page" : ""}</p>
    </div>
  );
}
