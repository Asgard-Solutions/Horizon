import { Film, PlayCircle, Tv } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { mediaUrl } from "../api";
import { progressRatio } from "../format";
import type { Progress } from "../types";

interface PosterProps {
  title: string;
  subtitle?: string | null;
  image: string | null;
  to: string;
  testId: string;
  progress?: Progress | null;
  kind?: "movie" | "show";
  wide?: boolean;
}

function Art({ image, title, kind, wide }: { image: string | null; title: string; kind: string; wide?: boolean }) {
  const [failed, setFailed] = useState(false);
  if (image && !failed) {
    return <img src={mediaUrl(image)} alt="" loading="lazy" onError={() => setFailed(true)} />;
  }
  const Icon = wide ? PlayCircle : kind === "show" ? Tv : Film;
  return (
    <div className="art-fallback">
      <Icon size={wide ? 34 : 40} strokeWidth={1.6} />
      <span>{title}</span>
    </div>
  );
}

export function PosterCard({ title, subtitle, image, to, testId, progress, kind = "movie", wide }: PosterProps) {
  const navigate = useNavigate();
  const ratio = progressRatio(progress ?? null);
  return (
    <button className={wide ? "card card--wide" : "card"} onClick={() => navigate(to)} data-testid={testId}>
      <div className="card-art">
        <Art image={image} title={title} kind={kind} wide={wide} />
        {progress?.watched && <span className="badge-watched">Watched</span>}
        {ratio > 0 && !progress?.watched && (
          <div className="card-progress"><div style={{ width: `${ratio * 100}%` }} /></div>
        )}
      </div>
      <div className="card-text">
        <span className="card-title">{title}</span>
        {subtitle && <span className="card-sub">{subtitle}</span>}
      </div>
    </button>
  );
}

export function Row({ title, children, testId }: { title: string; children: React.ReactNode; testId: string }) {
  return (
    <section className="row" data-testid={testId}>
      <h2 className="row-title">{title}</h2>
      <div className="row-track">{children}</div>
    </section>
  );
}
