import { useId } from "react";
import { Clapperboard, Tv } from "lucide-react";

/** Decorative category art; the surrounding link supplies its accessible name. */
export function MediaTypeIcon({ type }: { type: "movie" | "tv" }) {
  const gradient = `media-gold-${useId()}`;
  const Icon = type === "movie" ? Clapperboard : Tv;
  return <Icon className="hub-type-icon" strokeWidth={1.7} color={`url(#${gradient})`} aria-hidden="true" focusable="false">
    <defs><linearGradient id={gradient} x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stopColor="#fff0aa" /><stop offset=".35" stopColor="#ffd05c" />
      <stop offset=".75" stopColor="#eea51a" /><stop offset="1" stopColor="#bd7007" />
    </linearGradient></defs>
    <path className="hub-type-play" d={type === "movie" ? "M10 13.5 16 17 10 20Z" : "M10 10.5 16 14.5 10 18.5Z"}
      fill={`url(#${gradient})`} stroke="none" />
  </Icon>;
}
