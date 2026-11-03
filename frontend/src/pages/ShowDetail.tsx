import { Play, RotateCcw } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { ErrorState, Loading } from "../components/States";
import { DetailShell } from "../detail/DetailShell";
import { EpisodeJourney } from "../detail/EpisodeJourney";
import { WatchProgress } from "../detail/WatchProgress";
import { defaultEpisode, forgetShowFocus, nextUp, recallShowFocus, rememberShowFocus, type NextUp } from "../detail/nextUp";
import { episodeCode, formatTime, isPartial } from "../format";
import { useAsync } from "../hooks";
import type { Episode, ShowDetail as Show } from "../types";

const LABEL: Record<NextUp["mode"], string> = { resume: "Resume", next: "Next episode", start: "Play", rewatch: "Watch again" };

function NextUpActions({ up, autofocus, onPlay }: { up: NextUp; autofocus: boolean; onPlay: (ep: Episode, start: number, onCard: boolean) => void }) {
  const { ep, mode } = up;
  const code = episodeCode(ep.season_number, ep.episode_number, ep.episode_end);
  return (
    <div className="dt-nextup" data-testid="show-next-up" data-mode={mode}>
      <span className="dt-nextup-label">{mode === "resume" ? "Continue watching" : mode === "next" ? "Up next" : mode === "rewatch" ? "Seen it all" : "Start the series"}</span>
      <span className="dt-nextup-ep" data-testid="show-next-up-episode">{code}{ep.title ? ` · ${ep.title}` : ""}</span>
      {mode === "resume" && <WatchProgress progress={ep.progress} testId="show-next-up-progress" />}
      <div className="dt-actions">
        <button className="hbtn hbtn--primary dt-primary" data-autofocus={autofocus || undefined} data-testid="show-primary-action"
          onClick={() => onPlay(ep, mode === "resume" ? ep.progress!.position : 0, false)}>
          <Play size={26} fill="currentColor" /> <span>{LABEL[mode]}</span>
          <small>{mode === "resume" ? `from ${formatTime(ep.progress!.position)}` : code}</small>
        </button>
        {mode === "resume" && (
          <button className="hbtn" data-testid="show-start-over-button" onClick={() => onPlay(ep, 0, false)}>
            <RotateCcw size={22} /> Start episode over
          </button>
        )}
      </div>
    </div>
  );
}

function ShowView({ show }: { show: Show }) {
  const navigate = useNavigate();
  const { seasons } = show;
  const up = useMemo(() => nextUp(seasons), [seasons]);
  const [restored] = useState(() => recallShowFocus(show.id, seasons));
  const [seasonIdx, setSeasonIdx] = useState(restored?.season ?? up?.seasonIdx ?? 0);
  const [picked, setPicked] = useState<Record<number, number>>(() =>
    restored ? { [restored.season]: restored.episodeId } : up ? { [up.seasonIdx]: up.ep.id } : {});
  const season = seasons[seasonIdx];
  const selectedId = picked[seasonIdx] ?? defaultEpisode(season)?.id;

  const play = useCallback((ep: Episode, start: number, onCard: boolean) => {
    const idx = seasons.findIndex((s) => s.episodes.some((e) => e.id === ep.id));
    rememberShowFocus({ showId: show.id, season: idx, episodeId: ep.id, onCard });
    navigate(`/play/${ep.file_id}?start=${Math.floor(start)}`);
  }, [navigate, seasons, show.id]);
  const onSelect = useCallback((ep: Episode) => setPicked((p) => ({ ...p, [seasonIdx]: ep.id })), [seasonIdx]);
  const onCard = useCallback((ep: Episode) => play(ep, isPartial(ep.progress) ? ep.progress!.position : 0, true), [play]);

  return (
    <DetailShell backdrop={show.fanart_url} poster={season?.poster_url || show.poster_url} testId="show-detail-page" onLeave={forgetShowFocus}>
      <div className="dt-copy dt-copy--show">
        <span className="dt-eyebrow">Series</span>
        <h1 className="dt-title" data-testid="show-title">{show.title}</h1>
        <ul className="dt-chips" aria-label="Details">
          {show.year && <li>{show.year}</li>}
          <li>{show.season_count} season{show.season_count === 1 ? "" : "s"}</li>
          <li>{show.episode_count} episode{show.episode_count === 1 ? "" : "s"}</li>
        </ul>
        {show.plot && <p className="dt-plot" data-testid="show-plot">{show.plot}</p>}
        {up && <NextUpActions up={up} autofocus={!restored?.onCard} onPlay={play} />}
      </div>
      {season && (
        <EpisodeJourney seasons={seasons} seasonIdx={seasonIdx} onSeason={setSeasonIdx} selectedId={selectedId}
          onSelect={onSelect} onPlay={onCard} restoreId={restored?.onCard ? restored.episodeId : null} />
      )}
    </DetailShell>
  );
}

export default function ShowDetail() {
  const { id } = useParams();
  const { data, error, reload } = useAsync(() => api<Show>(`/api/shows/${id}`), [id]);
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data || String(data.id) !== id) return <Loading />;
  return <ShowView key={data.id} show={data} />;
}
