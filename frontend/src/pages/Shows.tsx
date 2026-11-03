import { api } from "../api";
import { PosterCard } from "../components/PosterCard";
import { Empty, ErrorState, Loading, PageHeader } from "../components/States";
import { useAsync } from "../hooks";
import type { ShowSummary } from "../types";

export default function Shows() {
  const { data, error, reload } = useAsync(() => api<ShowSummary[]>("/api/shows"), []);
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return <Loading />;
  return (
    <div className="page" data-testid="shows-page">
      <PageHeader title="TV Shows" meta={<span data-testid="shows-count">{data.length} shows</span>} />
      {data.length === 0 ? (
        <Empty title="No TV shows yet">
          <p>Name episodes like <code>Show Name - S01E02.mkv</code> and add their folder in Settings.</p>
        </Empty>
      ) : (
        <div className="grid" data-testid="shows-grid">
          {data.map((s) => (
            <PosterCard key={s.id} kind="show" title={s.title}
              subtitle={`${s.season_count} season${s.season_count === 1 ? "" : "s"} · ${s.episode_count} ep`}
              image={s.poster_url} to={`/shows/${s.id}`} testId={`show-card-${s.id}`} />
          ))}
        </div>
      )}
    </div>
  );
}
