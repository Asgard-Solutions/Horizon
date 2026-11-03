import { useState } from "react";
import { mediaUrl } from "../api";

const STOP = new Set(["the", "a", "an", "of", "and"]);
const monogram = (title: string) => {
  const words = title.split(/[\s\-_.:]+/).filter(Boolean);
  const main = words.filter((w) => !STOP.has(w.toLowerCase()));
  return (main.length ? main : words).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
};

/** Real local artwork, or a procedural monogram card; the title itself is always shown once, next to the art. */
export function TitleArt({ image, title, kind, className = "" }: { image: string | null; title: string; kind: string; className?: string }) {
  const [failed, setFailed] = useState(false);
  if (image && !failed) {
    return <img className={className} src={mediaUrl(image)} alt="" loading="lazy" decoding="async" onError={() => setFailed(true)} />;
  }
  return (
    <div className={`title-art ${className}`} data-testid="art-fallback" aria-hidden="true">
      <svg className="title-art-arc" viewBox="0 0 200 120" preserveAspectRatio="none">
        <path d="M-10 96 Q100 40 210 96" stroke="var(--h-color-accent-aurora)" strokeOpacity="0.55" strokeWidth="1.5" fill="none" />
        <path d="M-10 104 Q100 58 210 104" stroke="var(--h-color-accent-amber)" strokeOpacity="0.25" strokeWidth="1" fill="none" />
      </svg>
      <span className="title-art-mono">{monogram(title)}</span>
      <span className="title-art-kind">{kind === "show" ? "Series" : kind === "episode" ? "Episode" : "Movie"}</span>
    </div>
  );
}
