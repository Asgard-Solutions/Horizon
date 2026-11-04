interface SubtitleChoice { id: string; language: string | null }

export function positionSubtitleCues(cues: { line: number | "auto"; snapToLines: boolean; lineAlign: string }[], controlsVisible: boolean) {
  for (const cue of cues) {
    cue.snapToLines = false;
    cue.lineAlign = "end";
    cue.line = controlsVisible ? 60 : 85;
  }
}

export function automaticSubtitle(tracks: SubtitleChoice[], preference: "off" | "auto", languages: readonly string[]): string | null {
  if (preference !== "auto" || !tracks.length) return null;
  for (const language of languages) {
    const normalized = language.toLowerCase();
    const exact = tracks.find(t => t.language?.toLowerCase() === normalized);
    if (exact) return exact.id;
    const base = tracks.find(t => t.language?.toLowerCase().split("-")[0] === normalized.split("-")[0]);
    if (base) return base.id;
  }
  return (tracks.find(t => !t.language) ?? tracks[0]).id;
}

/** Preserve chapters/metadata while ensuring only the selected subtitle is visible. */
export function setSubtitleModes(tracks: Iterable<{ id: string; kind: string; mode: string }>, selected: string | null) {
  for (const track of tracks) {
    if (track.kind === "subtitles" || track.kind === "captions") track.mode = track.id === selected ? "showing" : "disabled";
  }
}

/** Track load/error do not bubble; subscribe directly, including already cached results. */
export function observeSubtitleLoad(track: EventTarget & { readyState: number }, finish: (failed: boolean) => void, timeout = 15000) {
  let done = false;
  let timer: ReturnType<typeof setTimeout> | undefined;
  const cleanup = () => {
    clearTimeout(timer);
    track.removeEventListener("load", onLoad);
    track.removeEventListener("error", onError);
  };
  const complete = (failed: boolean) => { if (!done) { done = true; cleanup(); finish(failed); } };
  const onLoad = () => complete(false);
  const onError = () => complete(true);
  track.addEventListener("load", onLoad);
  track.addEventListener("error", onError);
  timer = setTimeout(onError, timeout);
  if (track.readyState === 2) complete(false);
  else if (track.readyState === 3) complete(true);
  return () => { done = true; cleanup(); };
}
