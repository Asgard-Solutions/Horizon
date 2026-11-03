import { useEffect, useLayoutEffect, useRef } from "react";
import type { Episode, Season } from "../types";
import { EpisodeCard } from "./EpisodeCard";

interface Props {
  seasons: Season[];
  seasonIdx: number;
  onSeason: (i: number) => void;
  selectedId: number | undefined;
  onSelect: (ep: Episode) => void;
  onPlay: (ep: Episode) => void;
  restoreId: number | null;
}

const reduced = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const seasonLabel = (n: number) => (n === 0 ? "Specials" : `Season ${n}`);

/** Season tabs above a horizontal Episode Journey; Up from an episode returns to the selected season tab. */
export function EpisodeJourney({ seasons, seasonIdx, onSeason, selectedId, onSelect, onPlay, restoreId }: Props) {
  const track = useRef<HTMLDivElement>(null);
  const season = seasons[seasonIdx];
  const index = Math.max(0, season.episodes.findIndex((e) => e.id === selectedId));

  useLayoutEffect(() => {
    const el = track.current;
    const card = el?.querySelector<HTMLElement>(`[data-key="${selectedId}"]`);
    if (!el || !card) return;
    const left = card.parentElement!.offsetLeft - (el.clientWidth - card.offsetWidth) / 2;
    el.scrollTo({ left: Math.max(0, left), behavior: reduced() ? "auto" : "smooth" });
  }, [selectedId, seasonIdx]);

  // LB/RB (PageUp/PageDown) switch seasons; focus stays in the strip on the new season's selected episode.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "PageUp" && e.key !== "PageDown") return;
      const i = seasonIdx + (e.key === "PageDown" ? 1 : -1);
      if (i < 0 || i >= seasons.length) return;
      e.preventDefault();
      const inside = !!track.current?.contains(document.activeElement);
      onSeason(i);
      if (inside) window.setTimeout(() => track.current?.querySelector<HTMLElement>('[aria-current="true"], .ep')?.focus({ preventScroll: true }), 0);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [seasonIdx, seasons.length, onSeason]);

  return (
    <section className="journey" aria-label="Episodes" data-testid="episode-journey">
      <div className="journey-tabs" role="tablist" aria-label="Seasons" data-nav-prefer-selected data-testid="season-tabs">
        {seasons.map((s, i) => (
          <button key={s.id} role="tab" aria-selected={i === seasonIdx} className={i === seasonIdx ? "gtab gtab--active" : "gtab"}
            onFocus={() => i !== seasonIdx && onSeason(i)} onClick={() => onSeason(i)} data-testid={`season-tab-${s.season_number}`}>
            {seasonLabel(s.season_number)} <span className="gtab-count">{s.episodes.length}</span>
          </button>
        ))}
      </div>
      <div className="journey-track" ref={track} role="list" key={season.id} aria-label={seasonLabel(season.season_number)}
        data-nav-row data-nav-noscroll data-nav-prefer-selected data-nav-up='[data-testid="season-tabs"] [aria-selected="true"]'
        data-testid={`season-${season.season_number}-episodes`}>
        {season.episodes.map((ep, i) => (
          <EpisodeCard key={ep.id} ep={ep} dist={i - index} selected={ep.id === selectedId} autofocus={ep.id === restoreId}
            onSelect={onSelect} onPlay={onPlay} />
        ))}
      </div>
    </section>
  );
}
