import { mediaUrl } from "../api";
import { TitleArt } from "../components/TitleArt";
import type { AtlasNode, MediaItem } from "../types";

const KIND: Record<string, string> = { type: "Media", genre: "Genre", more: "More groups" };
const STATE: Record<string, string> = { watched: "Watched", in_progress: "In progress", unwatched: "Unwatched" };

/** Left-side reading panel for whatever the Atlas focus is on: real artwork and metadata only. */
export function InfoPanel({ node, level }: { node: AtlasNode | MediaItem | undefined; level: "overview" | "cluster" }) {
  if (!node) return <aside className="atlas-info" data-testid="atlas-info" />;
  if ("type" in node) {
    return (
      <aside className="atlas-info" data-testid="atlas-info" aria-live="polite">
        <div className="atlas-info-poster"><TitleArt image={node.poster_url} title={node.title} kind={node.type} /></div>
        <span className="atlas-info-kind">{node.type === "show" ? "Series" : "Movie"}</span>
        <h2 data-testid="atlas-info-title">{node.title}</h2>
        <p className="atlas-info-meta">{[node.year, node.type === "show" && node.episodes ? `${node.episodes} episodes` : null, STATE[node.state]].filter(Boolean).join(" · ")}</p>
        {node.genres.length > 0 && <p className="atlas-info-genres">{node.genres.join(" · ")}</p>}
        <p className="atlas-info-hint"><kbd>A</kbd> Open details</p>
      </aside>
    );
  }
  const kind = node.kind === "collection" ? (node.source === "folder" ? "Folder group" : "Collection") : KIND[node.kind];
  return (
    <aside className="atlas-info" data-testid="atlas-info" aria-live="polite">
      {node.posters.length > 0 && (
        <div className="atlas-info-fan" aria-hidden="true">
          {node.posters.map((p) => <img key={p} src={mediaUrl(p)} alt="" loading="lazy" />)}
        </div>
      )}
      <span className="atlas-info-kind">{kind}</span>
      <h2 data-testid="atlas-info-title">{node.label}</h2>
      <p className="atlas-info-meta" data-testid="atlas-info-count">{node.count} {node.kind === "more" ? "groups" : node.count === 1 ? "title" : "titles"}</p>
      <p className="atlas-info-hint"><kbd>A</kbd> {level === "overview" ? "Zoom in" : "Explore"}</p>
    </aside>
  );
}
