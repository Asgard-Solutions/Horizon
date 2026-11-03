import { AlertTriangle } from "lucide-react";
import { Link } from "react-router-dom";
import { useAuth } from "../App";
import type { HomeData } from "../types";

const plural = (n: number, w: string) => `${n} ${w}${n === 1 ? "" : "s"}`;

/** Slim, truthful status from real counts. Offline sources keep their entries and say so. */
export function LibraryStatus({ data }: { data: HomeData }) {
  const { auth } = useAuth();
  const { counts, sources } = data;
  return (
    <footer className="libstatus" data-testid="library-status">
      <span data-testid="home-counts">
        {plural(counts.movies, "movie")} · {counts.shows} series · {plural(counts.episodes, "episode")} · from {plural(sources.total, "folder")}
      </span>
      {sources.unreachable > 0 && (
        <span className="libstatus-warn" role="status" data-testid="library-status-unavailable">
          <AlertTriangle size={18} />
          {sources.unreachable === 1 ? "1 folder is unavailable." : `${sources.unreachable} folders are unavailable.`} Your library entries are still here.
          {auth.role === "host" && <Link to="/settings" data-testid="library-status-inspect-link">Inspect source</Link>}
        </span>
      )}
      <span className="hints" aria-hidden="true">
        <kbd>Enter</kbd> Select <kbd>Esc</kbd> Back <kbd>PgUp</kbd>/<kbd>PgDn</kbd> Groups · Controller <kbd>A</kbd> <kbd>B</kbd> <kbd>LB</kbd>/<kbd>RB</kbd> (untested on Xbox)
      </span>
    </footer>
  );
}
