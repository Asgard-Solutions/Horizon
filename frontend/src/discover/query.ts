import type { BrowseItem, MediaItem } from "../types";

export type View = "all" | "movies" | "shows" | "collections";
export type Sort = "title" | "added" | "year" | "progress";
export type FacetKey = "genre" | "decade" | "state" | "type";

export interface DiscoverQuery {
  view: View;
  sort: Sort;
  collection: number | null;
  filters: Record<FacetKey, string[]>;
}

export const NONE = "__none__";
export const VIEWS: { id: View; label: string }[] = [
  { id: "all", label: "All media" }, { id: "movies", label: "Movies" }, { id: "shows", label: "TV shows" }, { id: "collections", label: "Collections" },
];
export const SORTS: { id: Sort; label: string }[] = [
  { id: "title", label: "Title" }, { id: "added", label: "Recently added" }, { id: "year", label: "Release year" }, { id: "progress", label: "Watch progress" },
];
export const FACETS: { id: FacetKey; label: string; api: "genres" | "decades" | "states" | "types" }[] = [
  { id: "genre", label: "Genre", api: "genres" }, { id: "decade", label: "Year", api: "decades" },
  { id: "state", label: "Watched", api: "states" }, { id: "type", label: "Type", api: "types" },
];

export function facetLabel(facet: FacetKey, value: string): string {
  if (facet === "genre") return value === NONE ? "Uncategorized" : value;
  if (facet === "decade") return value === NONE ? "Year unknown" : `${value}s`;
  if (facet === "state") return { unwatched: "Unwatched", in_progress: "In progress", watched: "Watched" }[value] ?? value;
  return value === "movie" ? "Movies" : "TV shows";
}

const list = (v: string | null) => (v ? v.split(",").filter(Boolean) : []);

export function parseQuery(p: URLSearchParams): DiscoverQuery {
  const view = (VIEWS.some((v) => v.id === p.get("view")) ? p.get("view") : "all") as View;
  const sort = (SORTS.some((s) => s.id === p.get("sort")) ? p.get("sort") : "title") as Sort;
  const c = Number(p.get("collection"));
  return { view, sort, collection: Number.isInteger(c) && c > 0 ? c : null,
    filters: { genre: list(p.get("genre")), decade: list(p.get("decade")), state: list(p.get("state")), type: list(p.get("type")) } };
}

export function toParams(q: DiscoverQuery): URLSearchParams {
  const p = new URLSearchParams();
  if (q.view !== "all") p.set("view", q.view);
  if (q.sort !== "title") p.set("sort", q.sort);
  if (q.collection) p.set("collection", String(q.collection));
  for (const f of FACETS) if (q.filters[f.id].length) p.set(f.id, q.filters[f.id].join(","));
  return p;
}

export const activeFilters = (q: DiscoverQuery) =>
  FACETS.flatMap((f) => q.filters[f.id].map((value) => ({ facet: f.id, value })));

export const detailPath = (item: BrowseItem) =>
  item.type === "movie" ? `/movies/${item.id}` : item.type === "show" ? `/shows/${item.id}` : `/discover?collection=${item.id}`;

export function subtitle(item: BrowseItem): string {
  if (item.type === "collection") {
    const years = item.year_from && item.year_to && item.year_from !== item.year_to ? `${item.year_from}–${item.year_to}` : item.year_from ?? "";
    return [`${item.count} movie${item.count === 1 ? "" : "s"}`, years, item.source === "folder" ? "Folder" : null].filter(Boolean).join(" · ");
  }
  const m = item as MediaItem;
  return [m.year, m.type === "show" ? `Series · ${m.episodes} ep` : "Movie"].filter(Boolean).join(" · ");
}
