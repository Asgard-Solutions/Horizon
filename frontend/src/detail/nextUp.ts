import { isPartial } from "../format";
import type { Episode, Season } from "../types";

export type NextUpMode = "resume" | "next" | "start" | "rewatch";
export interface NextUp { ep: Episode; seasonIdx: number; mode: NextUpMode }

/** Derived only from real watch progress: resume a started episode, else the one after the last watched. */
export function nextUp(seasons: Season[]): NextUp | null {
  const regular = seasons.some((s) => s.season_number > 0);
  const list = seasons.flatMap((s, seasonIdx) =>
    regular && s.season_number === 0 ? [] : s.episodes.map((ep) => ({ ep, seasonIdx })));
  if (!list.length) return null;
  const resume = list.find((x) => isPartial(x.ep.progress));
  if (resume) return { ...resume, mode: "resume" };
  let last = -1;
  list.forEach((x, i) => { if (x.ep.progress?.watched) last = i; });
  if (last === -1) return { ...list[0], mode: "start" };
  const after = list.slice(last + 1).find((x) => !x.ep.progress?.watched);
  return after ? { ...after, mode: "next" } : { ...list[0], mode: "rewatch" };
}

export const defaultEpisode = (season: Season | undefined) =>
  season?.episodes.find((e) => isPartial(e.progress)) ?? season?.episodes.find((e) => !e.progress?.watched) ?? season?.episodes[0];

const KEY = "horizon-show-focus";
interface Saved { showId: number; season: number; episodeId: number; onCard: boolean }

export const rememberShowFocus = (s: Saved) => sessionStorage.setItem(KEY, JSON.stringify(s));
export const forgetShowFocus = () => sessionStorage.removeItem(KEY);
export function recallShowFocus(showId: number, seasons: Season[]): Saved | null {
  try {
    const s = JSON.parse(sessionStorage.getItem(KEY) ?? "null") as Saved | null;
    return s && s.showId === showId && seasons[s.season]?.episodes.some((e) => e.id === s.episodeId) ? s : null;
  } catch {
    return null;
  }
}
