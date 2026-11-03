export interface Progress {
  position: number;
  duration: number | null;
  watched: boolean;
}

export interface Movie {
  id: number;
  file_id: number;
  title: string;
  year: number | null;
  plot: string | null;
  filename: string;
  container: string;
  size: number;
  added_at: string;
  poster_url: string | null;
  fanart_url: string | null;
  progress: Progress | null;
}

export interface Episode {
  id: number;
  file_id: number;
  show_id: number;
  show_title: string;
  season_number: number;
  episode_number: number;
  episode_end: number | null;
  title: string | null;
  plot: string | null;
  filename: string;
  container: string;
  size: number;
  thumb_url: string | null;
  progress: Progress | null;
}

export interface ShowSummary {
  id: number;
  title: string;
  year: number | null;
  plot: string | null;
  poster_url: string | null;
  fanart_url: string | null;
  season_count: number;
  episode_count: number;
}

export interface Season {
  id: number;
  season_number: number;
  poster_url: string | null;
  episodes: Episode[];
}

export interface ShowDetail extends ShowSummary {
  seasons: Season[];
}

export type ContinueItem =
  | (Movie & { type: "movie" })
  | (Episode & { type: "episode"; show_poster_url: string | null; show_fanart_url: string | null });

export interface HomeData {
  continue_watching: ContinueItem[];
  recent_movies: Movie[];
  recent_episodes: Episode[];
  shows: ShowSummary[];
  counts: { movies: number; shows: number; episodes: number; libraries: number };
  sources: { total: number; unreachable: number; last_scan_at: string | null };
}

export interface Compatibility {
  status: "supported" | "maybe" | "unsupported" | "unknown";
  reasons: string[];
  mime: string;
  codecs: string | null;
}

export interface Probe {
  error?: string;
  format_name?: string;
  duration?: number | null;
  video?: { codec: string; profile?: string; width?: number; height?: number; pix_fmt?: string }[];
  audio?: { codec: string; channels?: number; language?: string }[];
  subtitles?: { codec: string; language?: string }[];
}

export interface PlaybackInfo {
  file_id: number;
  filename: string;
  container: string;
  size: number;
  stream_url: string;
  probe: Probe | null;
  compatibility: Compatibility;
  progress: Progress | null;
  context: { kind: string; title?: string; subtitle?: string; back?: string; next_file_id?: number | null; backdrop_url?: string | null };
}

export interface ScanSummary {
  files_found: number;
  added: number;
  updated: number;
  unchanged: number;
  removed: number;
  movies: number;
  episodes: number;
  errors: string[];
}

export interface Library {
  id: number;
  path: string;
  name: string;
  last_scan_at: string | null;
  last_scan_summary: ScanSummary | null;
  reachable: boolean;
  counts: { movies: number; episodes: number };
  scan?: ScanSummary | null;
}

export interface AuthStatus {
  role: "host" | "device" | "none";
  device_name: string | null;
  lan_enabled: boolean;
  pin_configured: boolean;
  locked_seconds: number;
  message: string | null;
}

export interface SystemInfo {
  version: string;
  platform: string;
  python: string;
  data_dir: string;
  ffprobe: { path: string | null; version: string | null };
  lan: { enabled: boolean; pin_configured: boolean; bind_host: string | null; port: number | null; restart_required: boolean; addresses: string[] };
}

export interface Device {
  id: number;
  name: string;
  created_at: string;
  last_seen_at: string | null;
  last_ip: string | null;
  revoked: number;
}
