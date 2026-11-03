import { Info, Play, RotateCcw, Tv } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { mediaUrl } from "../api";
import { TitleArt } from "../components/TitleArt";
import { progressRatio } from "../format";
import { rememberStageAction, type StageAction, type StageItem } from "./adapter";

/** The Stage: one selected real title. Selection never starts playback; actions do. */
export function StageHero({ item, autofocus }: { item: StageItem; autofocus: StageAction | null }) {
  const navigate = useNavigate();
  const backdrop = item.backdrop ?? item.poster;
  const ratio = progressRatio(item.progress);
  const PrimaryIcon = item.primary.label === "Explore series" ? Tv : item.primary.label === "Resume" ? RotateCcw : Play;
  return (
    <section className="stage" aria-live="polite" aria-label={`Selected: ${item.title}`} data-testid="stage-hero">
      <div className="stage-art" key={item.key} aria-hidden="true">
        {backdrop && <img className={item.backdrop ? "stage-backdrop" : "stage-backdrop stage-backdrop--poster"} src={mediaUrl(backdrop)} alt="" />}
        {!backdrop && <div className="stage-procedural" />}
        {!item.backdrop && (
          <div className="stage-poster"><TitleArt image={item.poster} title={item.title} kind={item.kind} /></div>
        )}
      </div>
      <div className="stage-scrim" aria-hidden="true" />
      <div className="stage-copy">
        <div className="stage-text" key={`copy-${item.key}`}>
        <span className="stage-eyebrow" data-testid="stage-eyebrow">{item.eyebrow}</span>
        <h1 className="stage-title" data-testid="stage-title">{item.title}</h1>
        {item.subtitle && <p className="stage-subtitle" data-testid="stage-subtitle">{item.subtitle}</p>}
        <ul className="stage-chips" aria-label="Details">
          {item.chips.map((c) => <li key={c}>{c}</li>)}
        </ul>
        {item.plot && <p className="stage-plot" data-testid="stage-plot">{item.plot}</p>}
        {ratio > 0 && !item.progress?.watched && (
          <div className="stage-progress" role="progressbar" aria-valuenow={Math.round(ratio * 100)} aria-valuemin={0} aria-valuemax={100}
            aria-label="Watched" data-testid="stage-progress"><span style={{ width: `${ratio * 100}%` }} /></div>
        )}
        </div>
        <div className="stage-actions">
          <button className="hbtn hbtn--primary" data-autofocus={autofocus === "primary" || undefined}
            onClick={() => { rememberStageAction("primary"); navigate(item.primary.to); }}
            data-testid="stage-primary-action">
            <PrimaryIcon size={24} strokeWidth={2.2} />
            <span>{item.primary.label}</span>
            {item.primary.hint && <small>{item.primary.hint}</small>}
          </button>
          {item.details && (
            <button className="hbtn" data-autofocus={autofocus === "details" || undefined}
              onClick={() => { rememberStageAction("details"); navigate(item.details!); }} data-testid="stage-details-action">
              <Info size={22} /> Details
            </button>
          )}
        </div>
      </div>
    </section>
  );
}
