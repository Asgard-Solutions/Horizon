import { CheckCircle2, Play } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, mediaUrl } from "../api";
import { ErrorState, Loading } from "../components/States";
import { episodeCode, formatTime, progressRatio } from "../format";
import { useAsync } from "../hooks";
import type { Episode, ShowDetail as Show } from "../types";

function EpisodeRow({ ep }: { ep: Episode }) {
  const navigate = useNavigate();
  const p = ep.progress;
  const resume = p && !p.watched && p.position > 10;
  return (
    <button className="episode" data-testid={`episode-row-${ep.id}`}
      onClick={() => navigate(`/play/${ep.file_id}${resume ? "" : "?start=0"}`)}>
      <div className="episode-thumb">
        {ep.thumb_url ? <img src={mediaUrl(ep.thumb_url)} alt="" loading="lazy" /> : <Play size={28} />}
      </div>
      <div className="episode-text">
        <span className="episode-code">{episodeCode(ep.season_number, ep.episode_number, ep.episode_end)}</span>
        <span className="episode-title">{ep.title || `Episode ${ep.episode_number}`}</span>
        <span className="episode-file">{ep.filename}</span>
        {resume && <span className="episode-resume">Resume from {formatTime(p!.position)}</span>}
      </div>
      {p?.watched && <CheckCircle2 className="episode-watched" size={26} aria-label="Watched" />}
      {resume && <div className="card-progress"><div style={{ width: `${progressRatio(p) * 100}%` }} /></div>}
    </button>
  );
}

export default function ShowDetail() {
  const { id } = useParams();
  const { data, error, reload } = useAsync(() => api<Show>(`/api/shows/${id}`), [id]);
  const [seasonIdx, setSeasonIdx] = useState(0);
  useEffect(() => setSeasonIdx(0), [id]);
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return <Loading />;
  const season = data.seasons[Math.min(seasonIdx, data.seasons.length - 1)];

  return (
    <div className="detail" data-testid="show-detail-page">
      {data.fanart_url && <div className="detail-backdrop" style={{ backgroundImage: `url(${mediaUrl(data.fanart_url)})` }} />}
      <div className="detail-body detail-body--show">
        <div className="detail-poster">
          {season?.poster_url || data.poster_url
            ? <img src={mediaUrl(season?.poster_url || data.poster_url)} alt="" />
            : <div className="art-fallback"><span>{data.title}</span></div>}
        </div>
        <div className="detail-info">
          <h1 data-testid="show-title">{data.title}</h1>
          <div className="detail-meta">
            {data.year && <span>{data.year}</span>}
            <span>{data.season_count} season{data.season_count === 1 ? "" : "s"}</span>
            <span>{data.episode_count} episodes</span>
          </div>
          {data.plot && <p className="detail-plot">{data.plot}</p>}
          <div className="season-tabs" role="tablist" data-testid="season-tabs">
            {data.seasons.map((s, i) => (
              <button key={s.id} role="tab" aria-selected={i === seasonIdx} data-autofocus={i === 0 ? true : undefined}
                className={i === seasonIdx ? "tab tab--active" : "tab"} onClick={() => setSeasonIdx(i)}
                onFocus={() => setSeasonIdx(i)} data-testid={`season-tab-${s.season_number}`}>
                {s.season_number === 0 ? "Specials" : `Season ${s.season_number}`}
              </button>
            ))}
          </div>
          {season && (
            <div className="episodes" data-testid={`season-${season.season_number}-episodes`}>
              {season.episodes.map((ep) => <EpisodeRow key={ep.id} ep={ep} />)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
