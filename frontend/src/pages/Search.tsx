import { Search as SearchIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate, useNavigationType, useSearchParams } from "react-router-dom";
import { api, mediaUrl } from "../api";
import { TitleArt } from "../components/TitleArt";
import { MediaCard } from "../discover/MediaCard";
import { detailPath } from "../discover/query";
import { episodeCode } from "../format";
import { Osk } from "../search/Osk";
import type { EpisodeHit, MediaItem, SearchResponse } from "../types";

const FOCUS_KEY = "horizon.search.focus";

function EpisodeResult({ ep, onOpen }: { ep: EpisodeHit; onOpen: () => void }) {
  const code = episodeCode(ep.season_number, ep.episode_number, null);
  return (
    <button className="sresult-ep" data-key={ep.key} onClick={onOpen} data-testid={`search-episode-${ep.id}`}
      aria-label={`${ep.show_title}, ${code}${ep.title ? `, ${ep.title}` : ""}`}>
      <span className="sresult-ep-art">{ep.thumb_url ? <img src={mediaUrl(ep.thumb_url)} alt="" loading="lazy" /> : <TitleArt image={null} title={ep.show_title} kind="episode" />}</span>
      <span className="sresult-ep-text"><b>{ep.show_title}</b><span>{code}{ep.title ? ` · ${ep.title}` : ""}</span></span>
    </button>
  );
}

function Section({ title, total, shown, children, testId }: { title: string; total: number; shown: number; children: React.ReactNode; testId: string }) {
  if (!total) return null;
  return (
    <section className="ssection" data-testid={testId}>
      <h2>{title} <span>{total > shown ? `${shown} of ${total}` : total}</span></h2>
      <div className="ssection-grid">{children}</div>
    </section>
  );
}

export default function Search() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const navType = useNavigationType();
  const [q, setQ] = useState(params.get("q") ?? "");
  const [res, setRes] = useState<SearchResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [inputMode, setInputMode] = useState<"none" | "search">("none");
  const [restore] = useState<{ key: string; index: number; scroll: number } | null>(() => {
    if (navType !== "POP") return null; // only Back restores; a fresh visit starts on the keyboard
    try { const s = JSON.parse(sessionStorage.getItem(FOCUS_KEY) ?? "null"); return s && s.q === (params.get("q") ?? "") ? s : null; } catch { return null; }
  });
  const seq = useRef(0);
  const restored = useRef(false);
  const lastResult = useRef<string | null>(restore?.key ?? null);
  const exitRight = () => {
    const all = Array.from(document.querySelectorAll<HTMLElement>(".search-results [data-key]"));
    const el = all.find((x) => x.dataset.key === lastResult.current) ?? all[0];
    el?.focus({ preventScroll: true });
    el?.scrollIntoView({ block: "nearest" });
    return !!el;
  };

  useEffect(() => {
    const n = ++seq.current;
    const t = window.setTimeout(() => {
      setParams(q ? { q } : {}, { replace: true });
      if (!q.trim()) { setRes(null); setBusy(false); return; }
      setBusy(true);
      api<SearchResponse>(`/api/search?q=${encodeURIComponent(q)}`).then((d) => { if (n === seq.current) { setRes(d); setBusy(false); } })
        .catch(() => n === seq.current && setBusy(false));
    }, 140);
    return () => window.clearTimeout(t);
  }, [q, setParams]);

  useEffect(() => {
    if (!res || !restore || restored.current) return;
    restored.current = true;
    // Exact result if it still exists, otherwise the result now at the same position, otherwise the keyboard.
    const all = Array.from(document.querySelectorAll<HTMLElement>(".search-results [data-key]"));
    const el = all.find((x) => x.dataset.key === restore.key) ?? all[Math.min(restore.index, all.length - 1)];
    if (el) { el.focus({ preventScroll: true }); window.scrollTo({ top: restore.scroll, behavior: "auto" }); }
    else document.querySelector<HTMLElement>(".osk-key")?.focus();
  }, [res, restore]);

  const open = (key: string, to: string) => {
    const index = Array.from(document.querySelectorAll<HTMLElement>(".search-results [data-key]")).findIndex((x) => x.dataset.key === key);
    sessionStorage.setItem(FOCUS_KEY, JSON.stringify({ q, key, index: Math.max(0, index), scroll: window.scrollY }));
    navigate(to);
  };
  const total = res ? res.totals.movies + res.totals.shows + res.totals.episodes : 0;
  // Physical typing while a result or other control is focused edits the query without moving focus.
  const onPageKey = (e: React.KeyboardEvent) => {
    const t = e.target as HTMLElement;
    if (t.tagName === "INPUT" || t.closest(".osk") || e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.key === "Backspace" && q) { e.preventDefault(); setQ((v) => v.slice(0, -1)); }
    else if (e.key.length === 1 && /[\p{L}\p{N} '\-.:&!?,]/u.test(e.key)) { e.preventDefault(); setQ((v) => v + e.key); }
  };

  return (
    <div className="page search" data-testid="search-page" onKeyDown={onPageKey}>
      <div className="search-input-col">
        <label className="search-field">
          <SearchIcon size={26} aria-hidden="true" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search titles, series, episodes" aria-label="Search the library"
            inputMode={inputMode} onPointerDown={() => setInputMode("search")} onBlur={() => setInputMode("none")}
            enterKeyHint="search" autoComplete="off" spellCheck={false} data-testid="search-input" />
        </label>
        <Osk onKey={(ch) => setQ((v) => v + ch)} onBackspace={() => setQ((v) => v.slice(0, -1))} onClear={() => setQ("")} onExitRight={exitRight} autofocus={!restore} />
        </div>
        <div className="search-results" aria-live="polite" aria-busy={busy} data-testid="search-results"
          onFocus={(e) => { const k = (e.target as HTMLElement).dataset.key; if (k) lastResult.current = k; }}>
        {!q.trim() ? (
          <div className="search-empty" data-testid="search-idle"><h2>Find anything in your library</h2><p>Type a title, a series or an episode name. Search runs on this PC, offline.</p></div>
        ) : res && total === 0 && !busy ? (
          <div className="search-empty" data-testid="search-no-results"><h2>No matches for “{q.trim()}”</h2><p>Check the spelling or try fewer words.</p>
            <button className="hbtn" onClick={() => setQ("")} data-testid="search-clear-button">Clear search</button></div>
        ) : res ? (
          <>
            <p className="search-count" data-testid="search-count">{busy ? "Searching…" : `${total} result${total === 1 ? "" : "s"}`}</p>
            <Section title="Movies" total={res.totals.movies} shown={res.movies.length} testId="search-section-movies">
              {res.movies.map((m: MediaItem, i) => <MediaCard key={m.key} item={m} index={i} onOpen={() => open(m.key, detailPath(m))} onFocus={() => undefined} />)}
            </Section>
            <Section title="Series" total={res.totals.shows} shown={res.shows.length} testId="search-section-shows">
              {res.shows.map((s, i) => <MediaCard key={s.key} item={s} index={i} onOpen={() => open(s.key, detailPath(s))} onFocus={() => undefined} />)}
            </Section>
            <Section title="Episodes" total={res.totals.episodes} shown={res.episodes.length} testId="search-section-episodes">
              {res.episodes.map((e) => <EpisodeResult key={e.key} ep={e} onOpen={() => open(e.key, `/shows/${e.show_id}`)} />)}
            </Section>
          </>
        ) : <p className="search-count">Searching…</p>}
      </div>
    </div>
  );
}
