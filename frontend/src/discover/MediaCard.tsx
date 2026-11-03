import { Check, Layers } from "lucide-react";
import { forwardRef } from "react";
import { TitleArt } from "../components/TitleArt";
import type { BrowseItem } from "../types";
import { subtitle } from "./query";

interface Props {
  item: BrowseItem;
  index: number;
  onOpen: () => void;
  onFocus: () => void;
}

/** One poster in the Discover wall: real art or the title monogram, title once below, truthful state. */
export const MediaCard = forwardRef<HTMLButtonElement, Props>(({ item, index, onOpen, onFocus }, ref) => {
  const state = item.type === "collection" ? null : item.state;
  return (
    <button ref={ref} className={`dcard${state ? ` dcard--${state}` : " dcard--collection"}`} data-index={index} data-key={item.key}
      onClick={onOpen} onFocus={onFocus} data-testid={`discover-card-${item.key}`}
      aria-label={`${item.title}. ${subtitle(item)}${state === "watched" ? ". Watched" : state === "in_progress" ? ". In progress" : ""}`}>
      <span className="dcard-art">
        <TitleArt image={item.poster_url} title={item.title} kind={item.type === "show" ? "show" : "movie"} />
        {item.type === "collection" && <span className={`dcard-badge dcard-badge--${item.source}`}><Layers size={14} /> {item.source === "nfo" ? "Collection" : "Folder"}</span>}
        {state === "watched" && <span className="dcard-badge dcard-badge--watched"><Check size={14} strokeWidth={3} /> Watched</span>}
        {state === "in_progress" && <span className="dcard-progress"><span style={{ width: `${Math.max(4, item.type !== "collection" ? item.progress * 100 : 0)}%` }} /></span>}
      </span>
      <span className="dcard-title">{item.title}</span>
      <span className="dcard-sub">{subtitle(item)}</span>
    </button>
  );
});
MediaCard.displayName = "MediaCard";
