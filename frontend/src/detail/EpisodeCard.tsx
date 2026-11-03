import { Check, Play } from "lucide-react";
import { mediaUrl } from "../api";
import { episodeCode, formatRuntime, isPartial, progressRatio, remainingLabel } from "../format";
import type { Episode } from "../types";

interface Props {
  ep: Episode;
  dist: number;
  selected: boolean;
  autofocus: boolean;
  onSelect: (ep: Episode) => void;
  onPlay: (ep: Episode) => void;
}

export function EpisodeCard({ ep, dist, selected, autofocus, onSelect, onPlay }: Props) {
  const p = ep.progress;
  const state = p?.watched ? "watched" : isPartial(p) ? "partial" : "unwatched";
  const code = episodeCode(ep.season_number, ep.episode_number, ep.episode_end);
  const title = ep.title || `Episode ${ep.episode_number}`;
  const runtime = formatRuntime(ep.runtime ?? p?.duration);
  const stateText = state === "watched" ? "Watched" : state === "partial" ? remainingLabel(p!) ?? "In progress" : "Unwatched";
  return (
    <div role="listitem" className="ep-slot">
      <button className={`ep ep--${state}${selected ? " ep--selected" : ""}`} data-key={ep.id} data-state={state}
        aria-current={selected ? "true" : undefined} data-autofocus={autofocus || undefined}
        style={{ "--dist": Math.min(Math.abs(dist), 4) } as React.CSSProperties}
        onFocus={() => onSelect(ep)} onClick={() => onPlay(ep)} data-testid={`episode-card-${ep.id}`}
        aria-label={`${code}, ${title}${runtime ? `, ${runtime}` : ""}. ${stateText}`}>
        <span className="ep-art">
          {ep.thumb_url ? <img src={mediaUrl(ep.thumb_url)} alt="" loading="lazy" decoding="async" />
            : <span className="ep-art-fallback" aria-hidden="true">{code}</span>}
          {state === "watched" && <span className="ep-badge ep-badge--watched" data-testid={`episode-watched-${ep.id}`}><Check size={16} strokeWidth={3} /> Watched</span>}
          {state === "partial" && <span className="ep-badge ep-badge--partial" data-testid={`episode-remaining-${ep.id}`}>{stateText}</span>}
          {state === "unwatched" && <span className="ep-dot" aria-hidden="true" />}
          {state === "partial" && <span className="ep-progress"><span style={{ width: `${progressRatio(p) * 100}%` }} /></span>}
          <span className="ep-play" aria-hidden="true"><Play size={26} fill="currentColor" /></span>
        </span>
        <span className="ep-text">
          <span className="ep-meta"><b>{code}</b>{runtime && <span data-testid={`episode-runtime-${ep.id}`}>{runtime}</span>}</span>
          <span className="ep-title">{title}</span>
          {ep.plot && <span className="ep-plot">{ep.plot}</span>}
        </span>
      </button>
    </div>
  );
}
