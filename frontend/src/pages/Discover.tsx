import { ArrowLeft } from "lucide-react";
import { useCallback, useMemo } from "react";
import { useLocation, useNavigate, useNavigationType, useSearchParams } from "react-router-dom";
import { ErrorState, Loading } from "../components/States";
import { FilterBar } from "../discover/FilterBar";
import { PosterGrid } from "../discover/PosterGrid";
import { detailPath, parseQuery, toParams, VIEWS, type DiscoverQuery, type View } from "../discover/query";
import { usePagedItems } from "../discover/usePagedItems";
import { useAuth } from "../App";
import type { BrowseItem } from "../types";
import { scopedPath } from "../home/context";
import { useMediaType } from "../home/useMediaType";

// One remembered position per result set (view + sort + filters + collection), so nested Back steps each restore their own tile.
const FOCUS_KEY = "horizon.discover.focus.v2";
type Spot = { index: number; scroll: number };
const readAll = (): Record<string, Spot> => { try { return JSON.parse(sessionStorage.getItem(FOCUS_KEY) ?? "{}") ?? {}; } catch { return {}; } };
const recall = (qs: string): Spot | null => readAll()[qs] ?? null;
const store = (qs: string, spot: Spot) => {
  const all = readAll();
  delete all[qs];
  const keys = Object.keys(all);
  for (const k of keys.slice(0, Math.max(0, keys.length - 24))) delete all[k];
  sessionStorage.setItem(FOCUS_KEY, JSON.stringify({ ...all, [qs]: spot }));
};

export default function Discover() {
  const navigate = useNavigate();
  const mediaType = useMediaType();
  const isHost = useAuth().auth.role === "host";
  const location = useLocation();
  const navType = useNavigationType();
  const [params, setParams] = useSearchParams();
  const query = useMemo(() => {
    const parsed = parseQuery(params);
    return mediaType ? { ...parsed, view: mediaType === "movie" ? "movies" as const : "shows" as const, filters: { ...parsed.filters, type: [] } } : parsed;
  }, [params, mediaType]);
  const qs = toParams(query).toString() + (mediaType ? `&media_type=${mediaType}` : "");
  const { first, error, total, facets, get, ensure } = usePagedItems(qs);
  // Back (POP) restores the remembered tile; opening a collection starts on its first tile;
  // changing tabs, sort or filters (REPLACE) leaves focus on the control that was used.
  const initial = useMemo<Spot | null>(() => (navType === "POP" ? recall(qs) : navType === "PUSH" && query.collection ? { index: 0, scroll: 0 } : null),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [location.key]);
  const remember = useCallback((i: number) => store(qs, { index: i, scroll: window.scrollY }), [qs]);

  const change = (q: DiscoverQuery) => {
    const next = toParams(q);
    if (mediaType) next.set("media", mediaType);
    setParams(next, { replace: true });
  };
  const setView = (v: View) => change({ ...query, view: v, collection: null, filters: { ...query.filters, type: [] } });
  const open = (item: BrowseItem, i: number) => {
    remember(i);
    navigate(scopedPath(item.type === "collection" ? `/discover?${new URLSearchParams({ collection: String(item.id) })}` : detailPath(item), mediaType));
  };
  const collectionName = first?.collection?.title;
  const filtered = Object.values(query.filters).some((f) => f.length);
  const libraryEmpty = !!first && total === 0 && !filtered && !query.collection && query.view === "all";
  const upTarget = query.view === "collections" && !query.collection ? '[data-testid="discover-views"] [aria-selected="true"]' : '[data-testid="discover-sort-button"]';

  return (
    <div className="page discover" data-testid="discover-page">
      <header className="discover-head">
        {query.collection ? (
          <div className="discover-crumb">
            <button className="hbtn hbtn--quiet" onClick={() => navigate(-1)} data-testid="discover-collection-back"><ArrowLeft size={20} /> Collections</button>
            <h1 className="discover-title" data-testid="discover-collection-title">{collectionName ?? "Collection"}</h1>
            {first?.collection && <span className="discover-source">{first.collection.source === "nfo" ? "Collection from NFO files" : "Folder group"}</span>}
          </div>
        ) : mediaType ? <h1 className="discover-title">{mediaType === "movie" ? "Movies" : "TV Shows"}</h1> : (
          <div className="journey-tabs discover-tabs" role="tablist" aria-label="Discover views" data-nav-row data-nav-prefer-selected data-testid="discover-views">
            {VIEWS.map((v) => (
              <button key={v.id} role="tab" aria-selected={query.view === v.id} className={query.view === v.id ? "gtab gtab--active" : "gtab"}
                data-autofocus={query.view === v.id || undefined} onClick={() => setView(v.id)} data-testid={`discover-view-${v.id}`}>{v.label}</button>
            ))}
          </div>
        )}
        <span className="discover-count" data-testid="discover-count" aria-live="polite">
          {first ? `${total} ${query.view === "collections" ? (total === 1 ? "collection" : "collections") : total === 1 ? "title" : "titles"}` : ""}
        </span>
      </header>
      {query.view !== "collections" && !libraryEmpty && <FilterBar query={query} facets={facets} onChange={change} />}
      {error ? <ErrorState message={error} />
        : !first ? <Loading />
        : libraryEmpty ? (
          <div className="discover-empty" data-testid="discover-empty-library">
            <h2>Your library is empty</h2>
            <p>Add a media folder on this PC or your network, and your movies and series will fill this wall.</p>
            <button className="hbtn hbtn--primary" onClick={() => navigate(scopedPath("/settings?section=libraries", mediaType))} data-testid="discover-add-folder">Library Settings</button>
          </div>
        ) : total === 0 ? (
          <div className="discover-empty" data-testid="discover-empty">
            <h2>{query.view === "collections" ? "No collections yet" : "Nothing matches"}</h2>
            <p>{query.view === "collections"
              ? "Collections appear when NFO files name a set, or when a folder holds several movies (if folder groups are on in Settings)."
              : filtered ? "Try removing a filter." : "Nothing of this kind in your library yet."}</p>
            {query.view === "collections" && isHost && (
              <div className="detail-actions" data-nav-row>
                <button className="hbtn hbtn--primary" onClick={() => navigate("/settings?section=libraries")} data-testid="collections-add-folder">Add media folder</button>
                <button className="hbtn" onClick={() => navigate("/settings?section=collections")} data-testid="collections-settings">Collection settings</button>
              </div>
            )}
          </div>
        ) : (
          <PosterGrid key={qs} total={total} get={get} ensure={ensure} onOpen={open} initialIndex={initial?.index ?? null} initialScroll={initial?.scroll ?? null}
            onFocusIndex={remember} navUp={upTarget} label={VIEWS.find((v) => v.id === query.view)?.label ?? "Titles"} />
        )}
    </div>
  );
}
