import { Check, RotateCcw, SlidersHorizontal, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useBack } from "../hooks";
import type { DiscoverPage } from "../types";
import { activeFilters, FACETS, facetLabel, SORTS, type DiscoverQuery, type FacetKey, type Sort } from "./query";

type Sheet = { kind: "sort" } | { kind: "facet"; facet: FacetKey };

function OptionSheet({ title, children, onClose }: { title: string; children: React.ReactNode; onClose: () => void }) {
  const box = useRef<HTMLDivElement>(null);
  useBack(() => { onClose(); return true; });
  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    (box.current?.querySelector<HTMLElement>(".dopt[aria-pressed='true']") ?? box.current?.querySelector<HTMLElement>(".dopt") ?? box.current?.querySelector<HTMLElement>("button"))?.focus();
    return () => prev?.focus({ preventScroll: true });
  }, []);
  return (
    <div className="dsheet-scrim" onClick={onClose} data-testid="filter-sheet-scrim">
      <div ref={box} className="dsheet" role="dialog" aria-modal="true" aria-label={title} data-nav-scope="modal"
        onClick={(e) => e.stopPropagation()} data-testid="filter-sheet">
        <div className="dsheet-head"><h2>{title}</h2>
          <button className="hbtn hbtn--quiet" onClick={onClose} data-testid="filter-sheet-close"><X size={20} /> Done</button></div>
        <div className="dsheet-options">{children}</div>
      </div>
    </div>
  );
}

interface Props {
  query: DiscoverQuery;
  facets: DiscoverPage["facets"];
  onChange: (q: DiscoverQuery) => void;
}

/** Sort + combinable filters (OR within a filter, AND across filters), shown as removable chips with Reset. */
export function FilterBar({ query, facets, onChange }: Props) {
  const [sheet, setSheet] = useState<Sheet | null>(null);
  const bar = useRef<HTMLDivElement>(null);
  const refocus = useRef<number | null>(null); // chip index to land on after a chip/reset removes the focused control
  const active = activeFilters(query);
  useEffect(() => {
    if (refocus.current === null) return;
    const chips = bar.current?.querySelectorAll<HTMLElement>(".dchip") ?? [];
    const target = chips[Math.min(refocus.current, chips.length - 1)] ?? bar.current?.querySelector<HTMLElement>("[data-testid='discover-sort-button']");
    refocus.current = null;
    target?.focus({ preventScroll: true });
  }, [active.length]);
  const toggle = (facet: FacetKey, value: string) => {
    const cur = query.filters[facet];
    onChange({ ...query, filters: { ...query.filters, [facet]: cur.includes(value) ? cur.filter((v) => v !== value) : [...cur, value] } });
  };
  const reset = () => { refocus.current = -1; onChange({ ...query, filters: { genre: [], decade: [], state: [], type: [] } }); };
  const facetList = FACETS.filter((f) => (f.id !== "type" || (query.view === "all" && !query.collection)) && (facets?.[f.api].length ?? 0) > 0
    && !(f.id === "genre" && facets!.genres.length === 1 && facets!.genres[0].value === "__none__"));

  return (
    <div className="dfilters" ref={bar} data-testid="discover-filters">
      <div className="dfilters-row">
        <button className="hbtn dfilter-btn" onClick={() => setSheet({ kind: "sort" })} data-testid="discover-sort-button">
          <SlidersHorizontal size={20} /> Sort: {SORTS.find((s) => s.id === query.sort)?.label}
        </button>
        {facetList.map((f) => (
          <button key={f.id} className={`hbtn dfilter-btn${query.filters[f.id].length ? " dfilter-btn--on" : ""}`}
            onClick={() => setSheet({ kind: "facet", facet: f.id })} data-testid={`discover-filter-${f.id}`}>
            {f.label}{query.filters[f.id].length ? <span className="dfilter-count">{query.filters[f.id].length}</span> : null}
          </button>
        ))}
        {active.length > 0 && (
          <button className="hbtn hbtn--quiet" onClick={reset} data-testid="discover-reset-filters"><RotateCcw size={18} /> Reset filters</button>
        )}
      </div>
      {active.length > 0 && (
        <ul className="dchips" aria-label="Active filters" data-testid="discover-active-filters">
          {active.map((a, i) => (
            <li key={`${a.facet}-${a.value}`}>
              <button className="dchip" onClick={() => { refocus.current = i; toggle(a.facet, a.value); }} aria-label={`Remove filter ${facetLabel(a.facet, a.value)}`}
                data-testid={`discover-chip-${a.facet}-${a.value}`}>{facetLabel(a.facet, a.value)} <X size={14} /></button>
            </li>
          ))}
        </ul>
      )}
      {sheet?.kind === "sort" && (
        <OptionSheet title="Sort by" onClose={() => setSheet(null)}>
          {SORTS.map((s) => (
            <button key={s.id} className="dopt" aria-pressed={query.sort === s.id} data-testid={`sort-option-${s.id}`}
              onClick={() => { onChange({ ...query, sort: s.id as Sort }); setSheet(null); }}>
              <span className="dopt-check">{query.sort === s.id && <Check size={18} />}</span>{s.label}
            </button>
          ))}
        </OptionSheet>
      )}
      {sheet?.kind === "facet" && facets && (
        <OptionSheet title={FACETS.find((f) => f.id === sheet.facet)!.label} onClose={() => setSheet(null)}>
          {facets[FACETS.find((f) => f.id === sheet.facet)!.api].map((o) => {
            const on = query.filters[sheet.facet].includes(o.value);
            return (
              <button key={o.value} className="dopt" aria-pressed={on} onClick={() => toggle(sheet.facet, o.value)}
                data-testid={`filter-option-${sheet.facet}-${o.value}`}>
                <span className="dopt-check">{on && <Check size={18} />}</span>{facetLabel(sheet.facet, o.value)}
                <span className="dopt-count">{o.count}</span>
              </button>
            );
          })}
        </OptionSheet>
      )}
    </div>
  );
}
