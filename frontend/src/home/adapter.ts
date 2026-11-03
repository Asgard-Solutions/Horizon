import { episodeCode, formatTime } from "../format";
import type { HomeData, Progress } from "../types";

/** Thin adapter between the real /api/home payload and the Home visuals. Only real fields are mapped. */
export interface StageItem {
  key: string;
  kind: "movie" | "show" | "episode";
  title: string;
  subtitle: string | null;
  eyebrow: string;
  chips: string[];
  plot: string | null;
  poster: string | null;
  backdrop: string | null;
  progress: Progress | null;
  primary: { label: "Resume" | "Play" | "Explore series"; hint: string | null; to: string };
  details: string | null;
}

export interface FilmGroup {
  id: "continue" | "recent" | "series";
  label: string;
  items: StageItem[];
}

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;

function remaining(p: Progress | null): string | null {
  if (!p?.duration || p.watched) return null;
  const mins = Math.round((p.duration - p.position) / 60);
  return mins > 0 ? `${mins} min left` : null;
}

const resumable = (p: Progress | null) => !!p && !p.watched && p.position > 10;

function playAction(fileId: number, p: Progress | null): StageItem["primary"] {
  return resumable(p)
    ? { label: "Resume", hint: `from ${formatTime(p!.position)}`, to: `/play/${fileId}?start=${Math.floor(p!.position)}` }
    : { label: "Play", hint: null, to: `/play/${fileId}?start=0` };
}

export function buildGroups(data: HomeData): FilmGroup[] {
  const cont: StageItem[] = data.continue_watching.map((c) =>
    c.type === "movie"
      ? {
          key: `cw-${c.file_id}`, kind: "movie", title: c.title, subtitle: null, eyebrow: "Continue watching",
          chips: ["Movie", ...(c.year ? [String(c.year)] : []), ...(remaining(c.progress) ? [remaining(c.progress)!] : [])],
          plot: c.plot, poster: c.poster_url, backdrop: c.fanart_url, progress: c.progress,
          primary: playAction(c.file_id, c.progress), details: `/movies/${c.id}`,
        }
      : {
          key: `cw-${c.file_id}`, kind: "episode", title: c.show_title,
          subtitle: `${episodeCode(c.season_number, c.episode_number, c.episode_end).replace("E", " E")}${c.title ? ` · ${c.title}` : ""}`,
          eyebrow: "Continue watching",
          chips: ["Episode", `S${String(c.season_number).padStart(2, "0")} E${String(c.episode_number).padStart(2, "0")}`,
            ...(remaining(c.progress) ? [remaining(c.progress)!] : [])],
          plot: c.plot, poster: c.show_poster_url ?? c.thumb_url, backdrop: c.show_fanart_url ?? c.thumb_url,
          progress: c.progress, primary: playAction(c.file_id, c.progress), details: `/shows/${c.show_id}`,
        }
  );
  const recent: StageItem[] = data.recent_movies.map((m) => ({
    key: `movie-${m.id}`, kind: "movie", title: m.title, subtitle: null, eyebrow: "Recently added",
    chips: ["Movie", ...(m.year ? [String(m.year)] : []), ...(remaining(m.progress) ? [remaining(m.progress)!] : [])],
    plot: m.plot, poster: m.poster_url, backdrop: m.fanart_url, progress: m.progress,
    primary: playAction(m.file_id, m.progress), details: `/movies/${m.id}`,
  }));
  const series: StageItem[] = data.shows.map((s) => ({
    key: `show-${s.id}`, kind: "show", title: s.title, subtitle: null, eyebrow: "Series",
    chips: ["Series", ...(s.year ? [String(s.year)] : []), plural(s.season_count, "season"), plural(s.episode_count, "episode")],
    plot: s.plot, poster: s.poster_url, backdrop: s.fanart_url, progress: null,
    primary: { label: "Explore series", hint: null, to: `/shows/${s.id}` }, details: null,
  }));
  return ([
    { id: "continue", label: "Continue watching", items: cont },
    { id: "recent", label: "Recently added movies", items: recent },
    { id: "series", label: "Series", items: series },
  ] as FilmGroup[]).filter((g) => g.items.length > 0);
}

const FOCUS_KEY = "horizon.home.focus";
const VIEW_KEY = "horizon.home.view";

export const rememberFocus = (group: string, key: string) => sessionStorage.setItem(FOCUS_KEY, JSON.stringify({ group, key }));
export function recallFocus(): { group: string; key: string } | null {
  try {
    return JSON.parse(sessionStorage.getItem(FOCUS_KEY) ?? "null");
  } catch {
    return null;
  }
}
export const loadView = (): "strip" | "grid" => (localStorage.getItem(VIEW_KEY) === "grid" ? "grid" : "strip");
const STAGE_KEY = "horizon.home.stageAction";
export type StageAction = "primary" | "details";
export const rememberStageAction = (a: StageAction) => sessionStorage.setItem(STAGE_KEY, a);
export const peekStageAction = (): StageAction | null => {
  const v = sessionStorage.getItem(STAGE_KEY);
  return v === "primary" || v === "details" ? v : null;
};
export const clearStageAction = () => sessionStorage.removeItem(STAGE_KEY);
export const saveView = (v: "strip" | "grid") => localStorage.setItem(VIEW_KEY, v);
