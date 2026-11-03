import { ArrowLeft, Maximize, Minimize, Pause, Play, RotateCcw, RotateCw, SkipBack, SkipForward, Volume2, VolumeX } from "lucide-react";
import type { RefObject } from "react";
import { formatTime } from "../format";

export interface ControlsState {
  playing: boolean;
  time: number;
  duration: number;
  buffered: number;
  volume: number;
  muted: boolean;
  fullscreen: boolean;
}

export type ControlsMode = "hidden" | "osd" | "expanded";

interface Props {
  s: ControlsState;
  mode: ControlsMode;
  eyebrow: string;
  title?: string;
  subtitle?: string;
  hasNext: boolean;
  playRef: RefObject<HTMLButtonElement | null>;
  onToggle: () => void;
  onSeekBy: (delta: number) => void;
  onSeekTo: (t: number) => void;
  onVolumeBy: (delta: number) => void;
  onMute: () => void;
  onFullscreen: () => void;
  onNext: () => void;
  onExit: () => void;
}

function Timeline({ s, active, onSeekTo, onToggle }: { s: ControlsState; active: boolean; onSeekTo: (t: number) => void; onToggle: () => void }) {
  const pct = s.duration ? (s.time / s.duration) * 100 : 0;
  const bufPct = s.duration ? (s.buffered / s.duration) * 100 : 0;
  const remaining = s.duration ? Math.max(0, s.duration - s.time) : null;
  const endsAt = remaining !== null ? new Date(Date.now() + remaining * 1000).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }) : null;
  return (
    <div className="pc-timeline" data-nav-skip={active ? undefined : true}>
      <button className="seekbar" data-seekbar role="slider" aria-label="Seek" aria-valuemin={0} tabIndex={active ? 0 : -1}
        aria-valuemax={Math.round(s.duration)} aria-valuenow={Math.round(s.time)}
        aria-valuetext={`${formatTime(s.time)} of ${formatTime(s.duration)}`} data-testid="player-seekbar"
        onClick={(e) => {
          const r = e.currentTarget.getBoundingClientRect();
          if (!e.clientX) onToggle();
          else if (s.duration) onSeekTo(((e.clientX - r.left) / r.width) * s.duration);
        }}>
        <span className="seek-buffer" style={{ width: `${bufPct}%` }} />
        <span className="seek-fill" style={{ width: `${pct}%` }} />
        <span className="seek-knob" style={{ left: `${pct}%` }} />
      </button>
      <div className="pc-times">
        <span data-testid="player-current-time">{formatTime(s.time)}</span>
        <span className="pc-times-mid">
          <span data-testid="player-duration">{formatTime(s.duration)}</span>
          {endsAt && <span data-testid="player-ends-at"> · Ends at {endsAt}</span>}
        </span>
        <span data-testid="player-remaining-time">−{formatTime(remaining)}</span>
      </div>
    </div>
  );
}

function ButtonRow(p: Props) {
  const { s } = p;
  const vol = s.muted ? 0 : s.volume;
  return (
    <div className="pc-buttons" data-testid="player-button-row">
      <button className="pc-btn" onClick={() => p.onSeekTo(0)} aria-label="Start over" data-testid="player-restart-button"><SkipBack size={26} /></button>
      <button className="pc-btn" onClick={() => p.onSeekBy(-10)} aria-label="Back 10 seconds" data-testid="player-rewind-button"><RotateCcw size={28} /><small>10</small></button>
      <button className="pc-btn pc-btn--main" ref={p.playRef} onClick={p.onToggle} aria-label={s.playing ? "Pause" : "Play"} data-testid="player-play-pause-button">
        {s.playing ? <Pause size={36} fill="currentColor" /> : <Play size={36} fill="currentColor" />}
      </button>
      <button className="pc-btn" onClick={() => p.onSeekBy(10)} aria-label="Forward 10 seconds" data-testid="player-forward-button"><RotateCw size={28} /><small>10</small></button>
      <span className="pc-spacer" />
      {p.hasNext && (
        <button className="hbtn" onClick={p.onNext} data-testid="player-next-episode-button"><SkipForward size={22} /> Next episode</button>
      )}
      <button className="pc-volume" data-volume role="slider" aria-label="Volume" aria-valuemin={0} aria-valuemax={100}
        aria-valuenow={Math.round(vol * 100)} onClick={p.onMute} data-testid="player-volume-control">
        {vol === 0 ? <VolumeX size={26} /> : <Volume2 size={26} />}
        <span className="pc-volume-track"><span style={{ width: `${vol * 100}%` }} /></span>
        <span className="pc-volume-num" data-testid="player-volume-value">{Math.round(vol * 100)}</span>
      </button>
      <button className="pc-btn" onClick={p.onFullscreen} aria-label="Fullscreen" data-testid="player-fullscreen-button">
        {s.fullscreen ? <Minimize size={26} /> : <Maximize size={26} />}
      </button>
    </div>
  );
}

/** Horizon OSD: hidden during playback, a minimal timeline on interaction, full controls after Up. */
export function PlayerControls(p: Props) {
  const expanded = p.mode === "expanded";
  return (
    <div className="pc" data-mode={p.mode} data-testid="player-controls">
      <div className="pc-top">
        <button className="pc-btn pc-btn--back" onClick={p.onExit} aria-label="Exit player" data-testid="player-exit-button"
          tabIndex={expanded ? 0 : -1} data-nav-skip={expanded ? undefined : true}>
          <ArrowLeft size={28} />
        </button>
        <div className="pc-titles">
          <span className="pc-eyebrow">{p.eyebrow}</span>
          <span className="pc-title" data-testid="player-title">{p.title}</span>
          {p.subtitle && <span className="pc-sub" data-testid="player-subtitle">{p.subtitle}</span>}
        </div>
      </div>
      <div className="pc-bottom">
        <Timeline s={p.s} active={expanded} onSeekTo={p.onSeekTo} onToggle={p.onToggle} />
        {expanded ? <ButtonRow {...p} /> : (
          <div className="pc-hint" data-testid="player-hint">
            <span><kbd>↑</kbd> More controls</span><span><kbd>←</kbd><kbd>→</kbd> 10 s</span>
            <span><kbd>A</kbd> / <kbd>Enter</kbd> {p.s.playing ? "Pause" : "Play"}</span><span><kbd>B</kbd> / <kbd>Esc</kbd> Back</span>
          </div>
        )}
      </div>
    </div>
  );
}
