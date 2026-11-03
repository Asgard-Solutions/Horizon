import { ArrowLeft } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ErrorState, Loading } from "../components/States";
import { FilterBar } from "../discover/FilterBar";
import { PosterGrid } from "../discover/PosterGrid";
import { detailPath, parseQuery, toParams, VIEWS, type DiscoverQuery, type View } from "../discover/query";
import { usePagedItems } from "../discover/usePagedItems";
import type { BrowseItem } from "../types";

const FOCUS_KEY = "horizon.discover.focus";
const recall = (qs: string): { index: number; scroll: number | null } | null => {
  try {
    const s = JSON.parse(sessionStorage.getItem(FOCUS_KEY) ?? "null");
    return s && s.qs === qs ? { index: s.index, scroll: s.scroll ?? null } : null;
  } catch { return null; }
};

export default function Discover() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const query = useMemo(() => parseQuery(params), [params]);
  const qs = toParams(query).toString();
  const { first, error, total, facets, get, ensure } = usePagedItems(qs);
  const [initial] = useState(() => recall(qs));
  const remember = useCallback((i: number) => sessionStorage.setItem(FOCUS_KEY, JSON.stringify({ qs, index: i, scroll: window.scrollY })), [qs]);

  const change = (q: DiscoverQuery) => setParams(toParams(q), { replace: true });
  const setView = (v: View) => change({ ...query, view: v, collection: null, filters: { ...query.filters, type: [] } });
  const open = (item: BrowseItem, i: number) => {
    remember(i);
    navigate(item.type === "collection" ? `/discover?${new URLSearchParams({ collection: String(item.id) })}` : detailPath(item));
  };
  const collectionName = first?.collection?.title;

  return (
    <div className="page discover" data-testid="discover-page">
      <header className="discover-head">
        {query.collection ? (
          <div className="discover-crumb">
            <button className="hbtn hbtn--quiet" onClick={() => navigate(-1)} data-testid="discover-collection-back"><ArrowLeft size={20} /> Collections</button>
            <h1 className="discover-title" data-testid="discover-collection-title">{collectionName ?? "Collection"}</h1>
            {first?.collection && <span className="discover-source">{first.collection.source === "nfo" ? "Collection from NFO files" : "Folder group"}</span>}
          </div>
        ) : (
          <div className="journey-tabs discover-tabs" role="tablist" aria-label="Discover views" data-nav-row data-nav-prefer-selected data-testid="discover-views">
            {VIEWS.map((v) => (
              <button key={v.id} role="tab" aria-selected={query.view === v.id} className={query.view === v.id ? "gtab gtab--active" : "gtab"}
                onClick={() => setView(v.id)} data-testid={`discover-view-${v.id}`}>{v.label}</button>
            ))}
          </div>
        )}
        <span className="discover-count" data-testid="discover-count" aria-live="polite">
          {first ? `${total} ${query.view === "collections" ? (total === 1 ? "collection" : "collections") : total === 1 ? "title" : "titles"}` : ""}
        </span>
      </header>
      {query.view !== "collections" && <FilterBar query={query} facets={facets} onChange={change} />}
      {error ? <ErrorState message={error} />
        : !first ? <Loading />
        : total === 0 ? (
          <div className="discover-empty" data-testid="discover-empty">
            <h2>{query.view === "collections" ? "No collections yet" : "Nothing matches"}</h2>
            <p>{query.view === "collections"
              ? "Collections appear when NFO files name a set, or when a folder holds several movies (if folder grouping is on in Library)."
              : facets && Object.values(query.filters).some((f) => f.length) ? "Try removing a filter." : "Add a media folder in Library to fill Discover."}</p>
          </div>
        ) : (
          <PosterGrid key={qs} total={total} get={get} ensure={ensure} onOpen={open} initialIndex={initial?.index ?? null} initialScroll={initial?.scroll ?? null} onFocusIndex={remember}
            label={VIEWS.find((v) => v.id === query.view)?.label ?? "Titles"} />
        )}
    </div>
  );
}
