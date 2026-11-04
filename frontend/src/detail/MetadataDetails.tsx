import type { TitleMetadata } from "../types";

/** Real NFO/provider information only; missing metadata leaves no decorative placeholders. */
export function MetadataDetails({ info }: { info: TitleMetadata }) {
  if (!info.cast?.length && info.rating == null && !info.premiered && !info.tagline) return null;
  return <div className="dt-metadata" data-testid="title-metadata">
    {info.tagline && <p><em>{info.tagline}</em></p>}
    <ul className="dt-chips" aria-label="Metadata details">
      {info.rating != null && <li>Rating {info.rating.toFixed(1)}/10</li>}
      {info.premiered && <li>Released {info.premiered}</li>}
    </ul>
    {!!info.cast?.length && <p className="lm-fine"><strong>Cast:</strong> {info.cast.slice(0, 8).map(p => `${p.name}${p.role ? ` (${p.role})` : ""}`).join(" · ")}</p>}
  </div>;
}
