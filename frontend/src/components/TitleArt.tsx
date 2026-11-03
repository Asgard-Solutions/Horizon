import { useState } from "react";
import { mediaUrl } from "../api";

/** Real local artwork, or a procedural typographic card built from the real title (never fake cover art). */
export function TitleArt({ image, title, kind, className = "" }: { image: string | null; title: string; kind: string; className?: string }) {
  const [failed, setFailed] = useState(false);
  if (image && !failed) {
    return <img className={className} src={mediaUrl(image)} alt="" loading="lazy" decoding="async" onError={() => setFailed(true)} />;
  }
  return (
    <div className={`title-art ${className}`} data-testid="art-fallback">
      <svg className="title-art-arc" viewBox="0 0 200 120" preserveAspectRatio="none" aria-hidden="true">
        <path d="M-10 96 Q100 40 210 96" stroke="var(--h-color-accent-aurora)" strokeOpacity="0.55" strokeWidth="1.5" fill="none" />
        <path d="M-10 104 Q100 58 210 104" stroke="var(--h-color-accent-amber)" strokeOpacity="0.25" strokeWidth="1" fill="none" />
      </svg>
      <span className="title-art-kind">{kind === "show" ? "Series" : kind === "episode" ? "Episode" : "Movie"}</span>
      <span className="title-art-title">{title}</span>
    </div>
  );
}
