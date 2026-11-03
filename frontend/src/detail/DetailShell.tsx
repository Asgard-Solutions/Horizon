import { useState, type CSSProperties, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { mediaUrl } from "../api";
import { useBack } from "../hooks";
import { useArtTone } from "./useArtTone";

interface Props {
  backdrop: string | null;
  poster: string | null;
  testId: string;
  onLeave?: () => void;
  children: ReactNode;
}

const reduced = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function ProceduralArt() {
  return (
    <svg className="dt-procedural" viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice" data-testid="detail-procedural-art">
      <path d="M-40 640 Q800 360 1640 640" stroke="var(--h-color-accent-aurora)" strokeOpacity="0.45" strokeWidth="2" fill="none" />
      <path d="M-40 690 Q800 450 1640 690" stroke="var(--h-color-accent-amber)" strokeOpacity="0.22" strokeWidth="1.5" fill="none" />
      <path d="M-40 740 Q800 540 1640 740" stroke="var(--h-color-border-strong)" strokeOpacity="0.35" strokeWidth="1" fill="none" />
    </svg>
  );
}

/** Full-screen cinematic canvas for detail pages: real art (or an elegant fallback), adaptive scrim, enter/leave motion. */
export function DetailShell({ backdrop, poster, testId, onLeave, children }: Props) {
  const navigate = useNavigate();
  const [leaving, setLeaving] = useState(false);
  const tone = useArtTone(mediaUrl(backdrop ?? poster));
  useBack(() => {
    if (leaving) return;
    onLeave?.();
    setLeaving(true);
    const idx = (window.history.state as { idx?: number } | null)?.idx ?? 0;
    window.setTimeout(() => (idx > 0 ? navigate(-1) : navigate("/", { replace: true })), reduced() ? 0 : 170);
  });
  return (
    <div className={leaving ? "dt dt--leaving" : "dt"} data-testid={testId} data-tone={tone.toFixed(2)}
      style={{ "--tone": tone } as CSSProperties}>
      <div className="dt-art" aria-hidden="true">
        {backdrop && <img className="dt-backdrop" src={mediaUrl(backdrop)} alt="" data-testid="detail-backdrop" />}
        {!backdrop && poster && <img className="dt-backdrop dt-backdrop--poster" src={mediaUrl(poster)} alt="" />}
        {!backdrop && !poster && <ProceduralArt />}
        {!backdrop && poster && <img className="dt-poster" src={mediaUrl(poster)} alt="" data-testid="detail-fallback-poster" />}
      </div>
      <div className="dt-scrim" aria-hidden="true" />
      <div className="dt-content">{children}</div>
    </div>
  );
}
