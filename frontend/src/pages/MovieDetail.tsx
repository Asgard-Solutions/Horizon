import { Play, RotateCcw } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { api, mediaUrl } from "../api";
import { TitleArt } from "../components/TitleArt";
import { CompatBadge } from "../components/CompatBadge";
import { ErrorState, Loading } from "../components/States";
import { formatBytes, formatTime } from "../format";
import { useAsync } from "../hooks";
import type { Movie, PlaybackInfo } from "../types";

export default function MovieDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data, error, reload } = useAsync(async () => {
    const movie = await api<Movie>(`/api/movies/${id}`);
    const playback = await api<PlaybackInfo>(`/api/files/${movie.file_id}/playback`);
    return { movie, playback };
  }, [id]);
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return <Loading />;
  const { movie, playback } = data;
  const resumable = movie.progress && !movie.progress.watched && movie.progress.position > 10;
  const video = playback.probe?.video?.[0];
  const audio = playback.probe?.audio?.[0];

  return (
    <div className="detail" data-testid="movie-detail-page">
      {movie.fanart_url && <div className="detail-backdrop" style={{ backgroundImage: `url(${mediaUrl(movie.fanart_url)})` }} />}
      <div className="detail-body">
        <div className="detail-poster">
          {movie.poster_url ? <img src={mediaUrl(movie.poster_url)} alt="" /> : <TitleArt image={null} title={movie.title} kind="movie" />}
        </div>
        <div className="detail-info">
          <h1 data-testid="movie-title">{movie.title}</h1>
          <div className="detail-meta">
            {movie.year && <span data-testid="movie-year">{movie.year}</span>}
            {playback.probe?.duration && <span>{formatTime(playback.probe.duration)}</span>}
            <span>{movie.container.toUpperCase()}</span>
            {video && <span>{video.codec?.toUpperCase()} {video.width}×{video.height}</span>}
            {audio && <span>{audio.codec?.toUpperCase()}</span>}
          </div>
          {movie.plot && <p className="detail-plot">{movie.plot}</p>}
          <div className="detail-actions">
            {resumable ? (
              <>
                <button className="btn btn--primary" data-autofocus data-testid="movie-resume-button"
                  onClick={() => navigate(`/play/${movie.file_id}?start=${Math.floor(movie.progress!.position)}`)}>
                  <Play size={24} /> Resume from {formatTime(movie.progress!.position)}
                </button>
                <button className="btn" data-testid="movie-start-over-button" onClick={() => navigate(`/play/${movie.file_id}?start=0`)}>
                  <RotateCcw size={22} /> Start over
                </button>
              </>
            ) : (
              <button className="btn btn--primary" data-autofocus data-testid="movie-play-button"
                onClick={() => navigate(`/play/${movie.file_id}?start=0`)}>
                <Play size={24} /> Play
              </button>
            )}
          </div>
          <CompatBadge compat={playback.compatibility} />
          <dl className="file-facts" data-testid="movie-file-facts">
            <dt>File</dt><dd data-testid="movie-filename">{movie.filename}</dd>
            <dt>Size</dt><dd>{formatBytes(movie.size)}</dd>
          </dl>
        </div>
      </div>
    </div>
  );
}
