import { useEffect, useLayoutEffect, useRef, useState, type FocusEvent, type KeyboardEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Compass, Database, Map as MapIcon, Search, Settings as SettingsIcon } from "lucide-react";
import { mediaUrl } from "../api";
import { episodeCode, formatTime } from "../format";
import { useBack } from "../hooks";
import type { ContinueItem } from "../types";
import { continueItems, focusFallback, hubPath, loadHomeSpot, saveHomeSpot, scopedPath, type MediaType } from "./context";
import { ResumeDialog } from "./ResumeDialog";
import { useHomeLibrary } from "./useHomeLibrary";
import { useHomeLayout } from "./useHomeLayout";

const navigation = [
  { id: "atlas", label: "Atlas", description: "Browse your indexed library", icon: MapIcon },
  { id: "discover", label: "Discover", description: "Explore your indexed library", icon: Compass },
  { id: "search", label: "Search", description: "Search your indexed library", icon: Search },
];

function ResumeArt({ url }: { url: string | null }) {
  const [failed, setFailed] = useState(false);
  return !url || failed ? <span className="hub-art-fallback">Artwork unavailable</span>
    : <img src={mediaUrl(url)} alt="" loading="lazy" onError={() => setFailed(true)} />;
}

export function HomeScreen({ type }: { type: MediaType | null }) {
  const navigate = useNavigate();
  const { stackedHome, stackedHub } = useHomeLayout();
  const { data, error, loading, reload } = useHomeLibrary(type);
  const rows = type && data ? continueItems(data.continue_watching, type) : [];
  const ids = rows.map(item => `resume-${item.file_id}`);
  const [modal, setModal] = useState<ContinueItem | null>(null);
  const [spot, setSpot] = useState(() => loadHomeSpot(type));
  const initialSpot = useRef(spot);
  const restored = useRef(false);
  const interacting = useRef(false);
  const restoring = useRef(false);
  const scene = useRef<HTMLDivElement>(null);
  const row = useRef<HTMLDivElement>(null);
  const lastBody = useRef(spot.focusId === "hub-retry" ? type ? spot.navigationId : "home-movies" : spot.focusId);
  const label = type === "tv" ? "TV Shows" : "Movies";
  const selectedCount = data ? type === "tv" ? data.counts.shows : data.counts.movies : null;
  const empty = !!type && !!data && selectedCount === 0;
  const fallback = spot.navigationId || "hub-atlas";
  const rowTarget = ids.includes(spot.focusId) ? spot.focusId : ids[Math.min(spot.resumeIndex, ids.length - 1)];
  const downTarget = rowTarget ?? (empty ? "hub-manage-sources" : error ? "hub-retry" : fallback);

  const focus = (id: string) => {
    const element = document.getElementById(id);
    if (!element) return false;
    restoring.current = true;
    element.focus({ preventScroll: true });
    restoring.current = false;
    return true;
  };
  useLayoutEffect(() => {
    const saved = initialSpot.current;
    focus(saved.focusId.startsWith("resume-") ? saved.navigationId : saved.focusId);
  }, []);
  useLayoutEffect(() => {
    if (!restored.current && (!initialSpot.current.focusId.startsWith("resume-") || !loading)) {
      const saved = initialSpot.current;
      if (!interacting.current) {
        const target = saved.focusId.startsWith("resume-") ? focusFallback(saved.focusId, saved.resumeIndex, ids, saved.navigationId)
          : document.getElementById(saved.focusId) ? saved.focusId : type ? saved.navigationId : "home-movies";
        if (row.current) row.current.scrollLeft = saved.scrollLeft;
        focus(target);
        const element = document.getElementById(target);
        if (element && row.current?.contains(element)) element.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "instant" });
        if (target !== saved.focusId) setSpot(current => ({ ...current, focusId: target }));
        lastBody.current = target;
      }
      restored.current = true;
    }
    if (restored.current && !loading && spot.focusId.startsWith("resume-") && !ids.includes(spot.focusId) && !modal && document.activeElement === document.body) {
      const target = focusFallback(spot.focusId, spot.resumeIndex, ids, fallback);
      focus(target);
      setSpot(current => ({ ...current, focusId: target }));
    }
    if (!error && !loading && spot.focusId === "hub-retry" && document.activeElement === document.body) {
      const target = lastBody.current;
      focus(target);
      setSpot(current => ({ ...current, focusId: target }));
    }
  });
  useEffect(() => { saveHomeSpot(type, spot); }, [type, spot]);
  useBack(() => {
    if (!type) return false;
    saveHomeSpot(null, { ...loadHomeSpot(null), focusId: type === "movie" ? "home-movies" : "home-tv" });
    navigate("/");
    return true;
  }, !!type);

  const remember = (event: FocusEvent) => {
    if (restoring.current || (event.target as HTMLElement).closest("[data-nav-scope='modal']")) return;
    const id = (event.target as HTMLElement).id;
    if (!id) return;
    if (id !== "hub-retry") lastBody.current = id;
    setSpot(current => ({ ...current, focusId: id, navigationId: navigation.some(item => `hub-${item.id}` === id) ? id : current.navigationId,
      resumeIndex: ids.includes(id) ? ids.indexOf(id) : current.resumeIndex }));
  };
  const headerWrapped = stackedHome;
  const mainKey = (event: KeyboardEvent) => {
    if (!event.defaultPrevented && ["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Tab"].includes(event.key)) interacting.current = true;
  };
  let status = loading && !data ? "Checking your library…" : "Library status unavailable";
  if (data) status = data.sources.total === 0 ? "No sources configured"
    : data.sources.unreachable > 0 ? `${data.sources.unreachable} source${data.sources.unreachable === 1 ? "" : "s"} unavailable · Indexed titles kept`
    : `${type ? `${selectedCount} ${type === "movie" ? "movies" : "TV shows"} · ` : ""}${data.sources.total} source${data.sources.total === 1 ? "" : "s"}`;
  if (error && data) status = "Saved library status · Refresh unavailable";
  const librarySettingsPath = scopedPath("/settings?section=libraries", type);
  return (
    <div className={`home-scene ${type ? "home-scene--hub" : "home-scene--selection"}`} ref={scene} data-testid={type ? "media-home-page" : "home-page"}
      data-media-type={type ?? ""} data-home-last-focus={spot.focusId} onFocusCapture={remember} onKeyDownCapture={mainKey}>
      {type && <button className="hub-breadcrumb" id="hub-back" onClick={() => { saveHomeSpot(null, { ...loadHomeSpot(null), focusId: type === "movie" ? "home-movies" : "home-tv" }); navigate("/"); }}
        data-nav-up="#global-home" data-nav-down={`#${fallback}`}>‹ Back to Home <span aria-hidden="true">/ {label}</span></button>}
      <h1 className="hub-heading">{type ? label : "What would you like to watch?"}</h1>
      <p className="hub-description">{type ? "Choose how to explore your library." : "Choose your library."}</p>
      <div className={`hub-choices ${type ? "hub-choices--navigation" : "hub-choices--types"}`}>
        {!type ? (["movie", "tv"] as const).map((choice, index) => {
          const id = choice === "movie" ? "home-movies" : "home-tv";
          const count = choice === "movie" ? data?.counts.movies : data?.counts.shows;
          const noun = choice === "movie" ? "movie" : "TV show";
          return <Link className={`hub-card hub-card--${choice}`} id={id} key={choice} to={hubPath(choice)} data-testid={id} data-autofocus={index === 0 || undefined}
            data-nav-up={stackedHome && index === 1 ? "#home-movies" : "#global-settings"}
            data-nav-down={stackedHome && index === 0 ? "#home-tv" : error ? "#hub-retry" : `#${id}`}
            data-nav-left={!stackedHome && index === 1 ? "#home-movies" : `#${id}`} data-nav-right={!stackedHome && index === 0 ? "#home-tv" : `#${id}`}>
            <strong>{choice === "movie" ? "Movies" : "TV Shows"}</strong>
            {count !== undefined && <span className="hub-card-count" data-testid={`${id}-count`}>{count.toLocaleString()} {noun}{count === 1 ? "" : "s"}</span>}
          </Link>;
        }) : navigation.map((item, index) => {
          const id = `hub-${item.id}`;
          const Icon = item.icon;
          const destination = item.id === "discover" ? `/discover?view=${type === "movie" ? "movies" : "shows"}` : `/${item.id}`;
          return <Link className={`hub-card hub-card--${item.id}`} id={id} key={item.id} data-testid={id} to={scopedPath(destination, type)} data-autofocus={index === 0 || undefined}
            data-nav-up={stackedHub && index > 0 ? `#hub-${navigation[index - 1].id}` : `#${index === 0 && !headerWrapped ? "global-home" : "global-settings"}`}
            data-nav-down={stackedHub && index < 2 ? `#hub-${navigation[index + 1].id}` : `#${downTarget}`}
            data-nav-left={!stackedHub && index > 0 ? `#hub-${navigation[index - 1].id}` : `#${id}`}
            data-nav-right={!stackedHub && index < 2 ? `#hub-${navigation[index + 1].id}` : `#${id}`}>
            <span className="hub-card-symbol" aria-hidden="true"><Icon strokeWidth={1.5} focusable="false" /></span>
            <strong>{item.label}</strong><span className="hub-card-description">{item.description}</span>
          </Link>;
        })}
      </div>
      {type && rows.length > 0 && <section className="hub-continue" aria-labelledby="hub-continue-heading" data-testid="continue-watching">
        <h2 id="hub-continue-heading">Continue Watching</h2>
        <div className="hub-resume-row" ref={row} data-nav-row data-nav-up={`#${fallback}`} data-nav-down={error ? "#hub-retry" : undefined}
          onScroll={() => setSpot(current => ({ ...current, scrollLeft: row.current?.scrollLeft ?? 0 }))}>
          {rows.map(item => {
            const title = item.type === "movie" ? item.title : item.show_title;
            const art = item.type === "movie" ? item.fanart_url ?? item.poster_url : item.thumb_url ?? item.show_fanart_url ?? item.show_poster_url;
            const metadata = [item.type === "episode" ? episodeCode(item.season_number, item.episode_number, item.episode_end) : null,
              `${formatTime(item.progress!.duration! - item.progress!.position)} left`].filter(Boolean).join(" · ");
            return <button className="hub-resume-card" id={`resume-${item.file_id}`} key={item.file_id} onClick={() => setModal(item)} data-testid={`resume-${item.file_id}`}
              aria-label={`${title}, ${metadata}, resume options`}>
              <span className="hub-resume-art"><ResumeArt key={art ?? "none"} url={art} /><span className="hub-progress" role="progressbar" aria-label={`${title} playback progress`}
                aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(item.progress!.position / item.progress!.duration! * 100)}><span style={{ width: `${item.progress!.position / item.progress!.duration! * 100}%` }} /></span></span>
              <strong>{title}</strong><span className="hub-resume-meta">{metadata}</span>
            </button>;
          })}
        </div>
      </section>}
      {type && empty && <section className="hub-empty" data-testid="hub-empty-library"><div><h2>{data!.sources.total === 0 ? "Set up your library" : `No ${type === "movie" ? "movies" : "TV shows"} indexed`}</h2>
        <p>{data!.sources.total === 0 ? "Add a drive or network folder in Settings." : "Add a source or check your library scan in Settings."}</p></div>
        <Link className="hub-action" id="hub-manage-sources" to={librarySettingsPath} data-nav-up={`#${fallback}`} data-nav-down={error ? "#hub-retry" : "#hub-manage-sources"}><SettingsIcon aria-hidden="true" focusable="false" />Library Settings</Link></section>}
      <footer className="hub-footer">
        {error ? <button className="hub-action hub-retry" id="hub-retry" onClick={() => { if (!loading) reload(); }} aria-disabled={loading} data-nav-up={`#${lastBody.current}`}
          data-testid="hub-retry" title={error}>{loading ? "Retrying…" : "Retry library status"}</button> : <span className="hub-footer-status" role="status">{!type && <Database aria-hidden="true" focusable="false" />}{status}</span>}
        <span className="hub-hints"><span className="hub-key-hints">Arrows Navigate · Enter Select{type ? " · Esc Back" : ""}</span><span className="hub-pad-hints">D-pad Navigate · A Select{type ? " · B Back" : ""}</span></span>
      </footer>
      {modal && type && <ResumeDialog item={modal} type={type} onClose={() => { setModal(null); reload(); }} />}
    </div>
  );
}
