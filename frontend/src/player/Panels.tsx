import { AlertOctagon, ArrowLeft, Play, RotateCcw } from "lucide-react";
import { formatTime } from "../format";
import type { PlaybackInfo } from "../types";

export function TechDetails({ info }: { info: PlaybackInfo }) {
  const v = info.probe?.video?.[0];
  const a = info.probe?.audio?.[0];
  return (
    <dl className="file-facts" data-testid="player-tech-details">
      <dt>File</dt><dd>{info.filename}</dd>
      <dt>Container</dt><dd>{info.container.toUpperCase()}</dd>
      <dt>Video</dt><dd>{v ? `${v.codec}${v.profile ? ` (${v.profile})` : ""} ${v.width ?? ""}×${v.height ?? ""}` : info.probe ? "none" : "not inspected"}</dd>
      <dt>Audio</dt><dd>{a ? `${a.codec}${a.channels ? `, ${a.channels} ch` : ""}` : info.probe ? "none" : "not inspected"}</dd>
    </dl>
  );
}

interface ProblemProps {
  info: PlaybackInfo;
  title: string;
  reasons: string[];
  onBack: () => void;
  onTryAnyway?: () => void;
  testId: string;
}

export function ProblemPanel({ info, title, reasons, onBack, onTryAnyway, testId }: ProblemProps) {
  return (
    <div className="player-panel" role="alert" data-testid={testId}>
      <AlertOctagon size={48} className="player-panel-icon" />
      <h1>{title}</h1>
      <ul className="player-panel-reasons" data-testid={`${testId}-reasons`}>
        {reasons.map((r) => <li key={r}>{r}</li>)}
      </ul>
      <TechDetails info={info} />
      <div className="detail-actions">
        <button className="btn btn--primary" data-autofocus onClick={onBack} data-testid={`${testId}-back-button`}>
          <ArrowLeft size={22} /> Go back
        </button>
        {onTryAnyway && (
          <button className="btn" onClick={onTryAnyway} data-testid={`${testId}-try-anyway-button`}>Try anyway</button>
        )}
      </div>
    </div>
  );
}

export function ResumePrompt({ position, onResume, onRestart }: { position: number; onResume: () => void; onRestart: () => void }) {
  return (
    <div className="player-panel" data-testid="resume-prompt">
      <h1>Pick up where you left off?</h1>
      <div className="detail-actions">
        <button className="btn btn--primary" data-autofocus onClick={onResume} data-testid="resume-prompt-resume-button">
          <Play size={22} /> Resume from {formatTime(position)}
        </button>
        <button className="btn" onClick={onRestart} data-testid="resume-prompt-restart-button">
          <RotateCcw size={22} /> Start from the beginning
        </button>
      </div>
    </div>
  );
}

export function mediaErrorMessage(err: MediaError | null): string {
  switch (err?.code) {
    case 1: return "Playback was aborted.";
    case 2: return "A network error interrupted streaming. Check that the host PC is running and reachable.";
    case 3: return "The browser could not decode this video (unsupported codec profile or a damaged file).";
    case 4: return "This browser cannot play this file's container or codecs. Transcoding is not available in Phase 0.";
    default: return "Playback failed for an unknown reason.";
  }
}
