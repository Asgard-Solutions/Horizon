import { FolderPlus } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../App";
import { PosterCard, Row } from "../components/PosterCard";
import { Empty, ErrorState, Loading, PageHeader } from "../components/States";
import { episodeCode } from "../format";
import { useAsync } from "../hooks";
import type { HomeData } from "../types";

export default function Home() {
  const { data, error, reload } = useAsync(() => api<HomeData>("/api/home"), []);
  const { auth } = useAuth();
  const navigate = useNavigate();
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return <Loading />;
  const { counts } = data;
  const empty = counts.movies + counts.episodes === 0;

  return (
    <div className="page" data-testid="home-page">
      <PageHeader
        title="Home"
        meta={<span data-testid="home-counts">{counts.movies} movies · {counts.shows} shows · {counts.episodes} episodes</span>}
      />
      {empty && (
        <Empty title={counts.libraries ? "No videos found in your folders yet" : "Your library is empty"}>
          <p>Add a folder that contains movies or TV episodes. Files are only read, never changed.</p>
          {auth.role === "host" && (
            <button className="btn btn--primary" data-autofocus onClick={() => navigate("/settings")} data-testid="home-add-folder-button">
              <FolderPlus size={22} /> Add a media folder
            </button>
          )}
        </Empty>
      )}
      {data.continue_watching.length > 0 && (
        <Row title="Continue watching" testId="row-continue-watching">
          {data.continue_watching.map((item) =>
            item.type === "movie" ? (
              <PosterCard key={`m${item.file_id}`} wide title={item.title} subtitle={item.year ? String(item.year) : null}
                image={item.fanart_url ?? item.poster_url} to={`/play/${item.file_id}`} progress={item.progress}
                testId={`continue-card-${item.file_id}`} />
            ) : (
              <PosterCard key={`e${item.file_id}`} wide title={item.show_title}
                subtitle={`${episodeCode(item.season_number, item.episode_number)}${item.title ? ` · ${item.title}` : ""}`}
                image={item.thumb_url} to={`/play/${item.file_id}`} progress={item.progress}
                testId={`continue-card-${item.file_id}`} />
            )
          )}
        </Row>
      )}
      {data.recent_movies.length > 0 && (
        <Row title="Recently added movies" testId="row-recent-movies">
          {data.recent_movies.map((m) => (
            <PosterCard key={m.id} title={m.title} subtitle={m.year ? String(m.year) : null} image={m.poster_url}
              to={`/movies/${m.id}`} progress={m.progress} testId={`home-movie-card-${m.id}`} />
          ))}
        </Row>
      )}
      {data.shows.length > 0 && (
        <Row title="TV shows" testId="row-shows">
          {data.shows.map((s) => (
            <PosterCard key={s.id} kind="show" title={s.title} subtitle={`${s.episode_count} episodes`}
              image={s.poster_url} to={`/shows/${s.id}`} testId={`home-show-card-${s.id}`} />
          ))}
        </Row>
      )}
      {data.recent_episodes.length > 0 && (
        <Row title="Recently added episodes" testId="row-recent-episodes">
          {data.recent_episodes.map((e) => (
            <PosterCard key={e.id} wide title={e.show_title}
              subtitle={`${episodeCode(e.season_number, e.episode_number, e.episode_end)}${e.title ? ` · ${e.title}` : ""}`}
              image={e.thumb_url} to={`/shows/${e.show_id}`} progress={e.progress} testId={`home-episode-card-${e.id}`} />
          ))}
        </Row>
      )}
    </div>
  );
}
