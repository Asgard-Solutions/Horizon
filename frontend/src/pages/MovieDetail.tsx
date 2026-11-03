import { Play, RotateCcw } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { CompatBadge } from "../components/CompatBadge";
import { ErrorState, Loading } from "../components/States";
import { DetailShell } from "../detail/DetailShell";
import { WatchProgress } from "../detail/WatchProgress";
import { formatBytes, formatRuntime, formatTime, isPartial } from "../format";
import { useAsync } from "../hooks";
import type { Movie, PlaybackInfo } from "../types";

function MovieActions({ movie }: { movie: Movie }) {
  const navigate = useNavigate();
  const play = (start: number) => navigate(`/play/${movie.file_id}?start=${Math.floor(start)}`);
  if (isPartial(movie.progress)) {
    return (
      <div className="dt-actions">
        <button className="hbtn hbtn--primary dt-primary" data-autofocus data-testid="movie-resume-button" onClick={() => play(movie.progress!.position)}>
          <Play size={26} fill="currentColor" /> <span>Resume</span> <small>from {formatTime(movie.progress!.position)}</small>
        </button>
        <button className="hbtn" data-testid="movie-start-over-button" onClick={() => play(0)}><RotateCcw size={22} /> Start over</button>
      </div>
    );
  }
  return (
    <div className="dt-actions">
      <button className="hbtn hbtn--primary dt-primary" data-autofocus data-testid="movie-play-button" onClick={() => play(0)}>
        <Play size={26} fill="currentColor" /> <span>{movie.progress?.watched ? "Play again" : "Play"}</span>
      </button>
    </div>
  );
}

export default function MovieDetail() {
  const { id } = useParams();
  const { data, error, reload } = useAsync(async () => {
    const movie = await api<Movie>(`/api/movies/${id}`);
    const playback = await api<PlaybackInfo>(`/api/files/${movie.file_id}/playback`);
    return { movie, playback };
  }, [id]);
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return <Loading />;
  const { movie, playback } = data;
  const video = playback.probe?.video?.[0];
  const audio = playback.probe?.audio?.[0];
  const runtime = formatRuntime(playback.probe?.duration ?? movie.runtime);

  return (
    <DetailShell backdrop={movie.fanart_url} poster={movie.poster_url} testId="movie-detail-page">
      <div className="dt-copy">
        <span className="dt-eyebrow">Movie</span>
        <h1 className="dt-title" data-testid="movie-title">{movie.title}</h1>
        <ul className="dt-chips" aria-label="Details" data-testid="movie-chips">
          {movie.year && <li data-testid="movie-year">{movie.year}</li>}
          {runtime ? <li data-testid="movie-runtime">{runtime}</li>
            : movie.runtime_status === "pending" && <li className="dt-chip-pending" data-testid="movie-runtime-pending">Reading length…</li>}
          {video?.height && <li>{video.height >= 2000 ? "4K" : `${video.height}p`}</li>}
          <li>{movie.container.toUpperCase()}</li>
          {audio && <li>{audio.codec?.toUpperCase()}{audio.channels ? ` ${audio.channels} ch` : ""}</li>}
        </ul>
        {movie.plot && <p className="dt-plot" data-testid="movie-plot">{movie.plot}</p>}
        <WatchProgress progress={movie.progress} testId="movie-progress" />
        <MovieActions movie={movie} />
        <div className="dt-tech">
          <CompatBadge compat={playback.compatibility} />
          <dl className="file-facts" data-testid="movie-file-facts">
            <dt>File</dt><dd data-testid="movie-filename">{movie.filename}</dd>
            <dt>Size</dt><dd>{formatBytes(movie.size)}</dd>
          </dl>
        </div>
      </div>
    </DetailShell>
  );
}
