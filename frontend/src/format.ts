export function formatTime(seconds: number | null | undefined): string {
  if (seconds == null || !isFinite(seconds)) return "--:--";
  const s = Math.max(0, Math.floor(seconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = String(s % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${sec}` : `${m}:${sec}`;
}

export function formatBytes(bytes: number): string {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let v = bytes;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(v < 10 && i > 0 ? 1 : 0)} ${units[i]}`;
}

export const episodeCode = (s: number, e: number, end?: number | null) =>
  `S${String(s).padStart(2, "0")}E${String(e).padStart(2, "0")}${end ? `-E${String(end).padStart(2, "0")}` : ""}`;

export const progressRatio = (p: { position: number; duration: number | null } | null) =>
  p && p.duration ? Math.min(1, p.position / p.duration) : 0;
