import { api } from "../api";
import { PosterCard } from "../components/PosterCard";
import { Empty, ErrorState, Loading, PageHeader } from "../components/States";
import { useAsync } from "../hooks";
import type { Movie } from "../types";

export default function Movies() {
  const { data, error, reload } = useAsync(() => api<Movie[]>("/api/movies"), []);
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return <Loading />;
  return (
    <div className="page" data-testid="movies-page">
      <PageHeader title="Movies" meta={<span data-testid="movies-count">{data.length} titles</span>} />
      {data.length === 0 ? (
        <Empty title="No movies yet"><p>Add a folder with movie files in Settings.</p></Empty>
      ) : (
        <div className="grid" data-testid="movies-grid">
          {data.map((m) => (
            <PosterCard key={m.id} title={m.title} subtitle={m.year ? String(m.year) : m.filename} image={m.poster_url}
              to={`/movies/${m.id}`} progress={m.progress} testId={`movie-card-${m.id}`} />
          ))}
        </div>
      )}
    </div>
  );
}
