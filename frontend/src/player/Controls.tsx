import { ArrowLeft, FastForward, Maximize, Minimize, Pause, Play, Rewind, SkipForward, Volume2, VolumeX } from "lucide-react";
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

interface Props {
  s: ControlsState;
  visible: boolean;
  title?: string;
  subtitle?: string;
  hasNext: boolean;
  seekRef: RefObject<HTMLButtonElement | null>;
  onToggle: () => void;
  onSeekBy: (delta: number) => void;
  onSeekTo: (t: number) => void;
  onVolumeBy: (delta: number) => void;
  onMute: () => void;
  onFullscreen: () => void;
  onNext: () => void;
  onExit: () => void;
}

export function PlayerControls(p: Props) {
  const { s } = p;
  const pct = s.duration ? (s.time / s.duration) * 100 : 0;
  const bufPct = s.duration ? (s.buffered / s.duration) * 100 : 0;
  const vol = s.muted ? 0 : s.volume;
  return (
    <div className={p.visible ? "pc pc--visible" : "pc"} data-testid="player-controls">
      <div className="pc-top">
        <button className="icon-btn" onClick={p.onExit} aria-label="Exit player" data-testid="player-exit-button">
          <ArrowLeft size={30} />
        </button>
        <div className="pc-titles">
          <span className="pc-title" data-testid="player-title">{p.title}</span>
          {p.subtitle && <span className="pc-sub">{p.subtitle}</span>}
        </div>
      </div>
      <div className="pc-bottom">
        <div className="pc-seek">
          <span className="pc-time" data-testid="player-current-time">{formatTime(s.time)}</span>
          <button
            className="seekbar" data-seekbar role="slider" aria-label="Seek" aria-valuemin={0}
            aria-valuemax={Math.round(s.duration)} aria-valuenow={Math.round(s.time)}
            aria-valuetext={`${formatTime(s.time)} of ${formatTime(s.duration)}`} data-testid="player-seekbar"
            ref={p.seekRef}
            onClick={(e) => {
              const r = e.currentTarget.getBoundingClientRect();
              if (!e.clientX) p.onToggle();
              else if (s.duration) p.onSeekTo(((e.clientX - r.left) / r.width) * s.duration);
            }}
          >
            <span className="seek-buffer" style={{ width: `${bufPct}%` }} />
            <span className="seek-fill" style={{ width: `${pct}%` }} />
            <span className="seek-knob" style={{ left: `${pct}%` }} />
          </button>
          <span className="pc-time" data-testid="player-duration">{formatTime(s.duration)}</span>
        </div>
        <div className="pc-buttons">
          <button className="icon-btn" onClick={() => p.onSeekBy(-10)} aria-label="Back 10 seconds" data-testid="player-rewind-button"><Rewind size={30} /></button>
          <button className="icon-btn icon-btn--main" onClick={p.onToggle} aria-label={s.playing ? "Pause" : "Play"} data-testid="player-play-pause-button">
            {s.playing ? <Pause size={38} /> : <Play size={38} />}
          </button>
          <button className="icon-btn" onClick={() => p.onSeekBy(30)} aria-label="Forward 30 seconds" data-testid="player-forward-button"><FastForward size={30} /></button>
          <button
            className="volume" data-volume role="slider" aria-label="Volume" aria-valuemin={0} aria-valuemax={100}
            aria-valuenow={Math.round(vol * 100)} onClick={p.onMute} data-testid="player-volume-control"
          >
            {vol === 0 ? <VolumeX size={28} /> : <Volume2 size={28} />}
            <span className="volume-track"><span style={{ width: `${vol * 100}%` }} /></span>
            <span className="volume-num" data-testid="player-volume-value">{Math.round(vol * 100)}</span>
          </button>
          <span className="pc-spacer" />
          {p.hasNext && (
            <button className="btn" onClick={p.onNext} data-testid="player-next-episode-button"><SkipForward size={24} /> Next episode</button>
          )}
          <button className="icon-btn" onClick={p.onFullscreen} aria-label="Fullscreen" data-testid="player-fullscreen-button">
            {s.fullscreen ? <Minimize size={30} /> : <Maximize size={30} />}
          </button>
        </div>
        <div className="pc-hint">←/→ seek (on the bar) · Enter play/pause · ↑/↓ controls · F fullscreen · M mute · Esc back</div>
      </div>
    </div>
  );
}
