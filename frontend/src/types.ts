export interface Progress {
  position: number;
  duration: number | null;
  watched: boolean;
}

export interface TitleMetadata {
  tagline?: string | null;
  cast?: { name: string; role: string }[];
  rating?: number | null;
  premiered?: string | null;
  external_ids?: Record<string, string>;
}

export interface Movie extends TitleMetadata {
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
  runtime: number | null;
  runtime_status: "known" | "pending" | "unknown";
}

export interface Episode extends TitleMetadata {
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
  runtime: number | null;
  runtime_status: "known" | "pending" | "unknown";
}

export interface ShowSummary extends TitleMetadata {
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
  context: { kind: string; title?: string; subtitle?: string; back?: string; next_file_id?: number | null; next_title?: string | null; backdrop_url?: string | null };
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
  status?: "complete" | "partial" | "cancelled" | "unreachable" | "failed" | "removed";
  finished_at?: string;
}

export interface ScanJob {
  id: string;
  library_id: number;
  library_name: string;
  path: string;
  state: "queued" | "running" | "done" | "cancelled" | "unreachable" | "failed" | "removed";
  files_found: number;
  current: string;
  started_at: string | null;
  finished_at: string | null;
  summary: ScanSummary | null;
}

export interface ScanStatus { running: ScanJob | null; queued: ScanJob[]; recent: ScanJob[] }

export interface MetadataStatus {
  available: boolean; workers: number; pending: number; known: number; unknown: number; active: number; unreachable: number; paused: boolean;
}

export interface Preferences {
  resume: "ask" | "auto";
  autoplay_next: boolean;
  skip_seconds: 10 | 30 | 60;
  watched_threshold: "90" | "95" | "end";
  subtitles: "off" | "auto";
}

export interface LocalSubtitle {
  id: string;
  label: string;
  language: string | null;
  url: string;
}

export interface Library {
  id: number;
  path: string;
  name: string;
  last_scan_at: string | null;
  last_success_at: string | null;
  last_scan_summary: ScanSummary | null;
  reachable: boolean;
  network: boolean;
  counts: { movies: number; episodes: number };
  details: { files: number; shows: number; metadata_pending: number; size_bytes: number };
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

export type WatchState = "unwatched" | "in_progress" | "watched";

export interface MediaItem {
  key: string;
  type: "movie" | "show";
  id: number;
  title: string;
  year: number | null;
  genres: string[];
  collection_id: number | null;
  poster_url: string | null;
  fanart_url: string | null;
  added_at: string | null;
  state: WatchState;
  progress: number;
  episodes: number | null;
}

export interface CollectionItem {
  key: string;
  type: "collection";
  id: number;
  title: string;
  source: "nfo" | "folder";
  count: number;
  year_from: number | null;
  year_to: number | null;
  poster_url: string | null;
}

export type BrowseItem = MediaItem | CollectionItem;

export interface FacetValue { value: string; count: number }

export interface DiscoverPage {
  view: string;
  total: number;
  offset: number;
  items: BrowseItem[];
  facets: { genres: FacetValue[]; decades: FacetValue[]; states: FacetValue[]; types: FacetValue[] } | null;
  collection?: { id: number; title: string; source: "nfo" | "folder" } | null;
}

export interface EpisodeHit {
  key: string;
  type: "episode";
  id: number;
  show_id: number;
  show_title: string;
  season_number: number;
  episode_number: number;
  title: string | null;
  file_id: number;
  thumb_url: string | null;
  watched: boolean;
}

export interface SearchResponse {
  query: string;
  movies: MediaItem[];
  shows: MediaItem[];
  episodes: EpisodeHit[];
  totals: { movies: number; shows: number; episodes: number };
}

export interface AtlasNode {
  id: string;
  kind: "type" | "genre" | "collection" | "more";
  value: string | number;
  label: string;
  count: number;
  source?: "nfo" | "folder";
  posters: string[];
  children?: AtlasNode[];
}

export interface AtlasData {
  total: number;
  rings: { id: string; label: string; nodes: AtlasNode[] }[];
  sources: { total: number; unreachable: number };
}
