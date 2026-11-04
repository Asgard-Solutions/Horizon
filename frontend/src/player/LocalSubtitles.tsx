import { useEffect, useRef, useState, type RefObject } from "react";
import { api, mediaUrl } from "../api";
import { useAsync, useBack } from "../hooks";
import type { LocalSubtitle, Preferences } from "../types";
import { automaticSubtitle, observeSubtitleLoad, positionSubtitleCues, setSubtitleModes } from "./subtitles";

export function useLocalSubtitles(fileId: string | undefined, prefs: Preferences | null, video: RefObject<HTMLVideoElement | null>, active: boolean, controlsVisible: boolean) {
  const { data, loading, error, reload } = useAsync(
    () => api<{ tracks: LocalSubtitle[] }>(`/api/files/${fileId}/subtitles`).then(result => ({ ...result, fileId })), [fileId]);
  const tracks = data && data.fileId === fileId ? data.tracks : [];
  const [choice, setChoice] = useState<{ fileId: string | undefined; id: string | null } | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [loaded, setLoaded] = useState<{ key: string; error: boolean } | null>(null);
  const auto = automaticSubtitle(tracks, prefs?.subtitles ?? "off", navigator.languages ?? [navigator.language]);
  const requested = choice && choice.fileId === fileId ? choice.id : auto;
  const selected = tracks.find(track => track.id === requested) ?? null;
  const key = `${fileId}:${selected?.id}:${attempt}`;
  const currentKey = useRef(key);
  currentKey.current = key;
  const trackError = selected && loaded?.key === key && loaded.error ? "This subtitle could not be loaded. The file may have changed, be unreadable or be unavailable." : null;
  const trackLoading = !!selected && loaded?.key !== key;

  useEffect(() => {
    if (!active) return;
    if (video.current) setSubtitleModes(Array.from(video.current.textTracks), selected?.id ?? null);
    if (!selected) return;
    const element = video.current?.querySelector<HTMLTrackElement>('[data-testid="player-local-track"]');
    if (!element) return;
    const position = () => positionSubtitleCues(Array.from(element.track.cues ?? []) as VTTCue[], controlsVisible);
    position();
    return observeSubtitleLoad(element, failed => {
      if (currentKey.current !== key) return;
      if (!failed) position();
      setLoaded({ key, error: failed });
      if (video.current) setSubtitleModes(Array.from(video.current.textTracks), failed ? null : selected.id);
    });
  }, [key, selected?.id, video, active, controlsVisible]);
  return {
    tracks, loading, error, reload, selected, trackError, trackLoading,
    select: (id: string | null) => { setChoice({ fileId, id }); setAttempt(n => n + 1); },
    retry: () => setAttempt(n => n + 1),
    track: selected ? <track key={key} id={selected.id} kind="subtitles" label={selected.label} srcLang={selected.language ?? "und"}
      src={mediaUrl(selected.url)} default data-testid="player-local-track" /> : null,
  };
}

export function SubtitleDialog({ subtitles, onClose }: {
  subtitles: ReturnType<typeof useLocalSubtitles>; onClose: () => void;
}) {
  const root = useRef<HTMLDivElement>(null);
  useBack(onClose);
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    root.current?.querySelector<HTMLElement>('[aria-pressed="true"]')?.focus({ preventScroll: true });
    return () => { if (opener?.isConnected) opener.focus({ preventScroll: true }); };
  }, []);
  useEffect(() => {
    if (root.current && !root.current.contains(document.activeElement))
      root.current.querySelector<HTMLElement>('[aria-pressed="true"]')?.focus({ preventScroll: true });
  }, [subtitles.loading, subtitles.error]);
  return <div className="modal-backdrop" data-nav-scope="modal" data-testid="player-subtitles-dialog"
    onKeyDown={event => {
      if (event.key !== "Tab") return;
      const buttons = Array.from(root.current?.querySelectorAll<HTMLButtonElement>("button") ?? []);
      const index = buttons.indexOf(document.activeElement as HTMLButtonElement);
      event.preventDefault();
      buttons[(index + (event.shiftKey ? -1 : 1) + buttons.length) % buttons.length]?.focus();
    }}>
    <div className="modal subtitle-dialog" role="dialog" aria-modal="true" aria-labelledby="subtitle-dialog-title" ref={root}>
      <h2 id="subtitle-dialog-title">Subtitles</h2>
      <p className="muted">Local .srt and .vtt files beside this video.</p>
      <div className="subtitle-options">
        <button className="btn" aria-pressed={!subtitles.selected} onClick={() => subtitles.select(null)} data-testid="subtitle-off">Off</button>
        {!subtitles.error && subtitles.tracks.map(track => <button key={track.id} className="btn"
          aria-pressed={subtitles.selected?.id === track.id} onClick={() => subtitles.select(track.id)} data-testid={`subtitle-option-${track.id}`}>
          {track.label}
        </button>)}
      </div>
      {subtitles.loading && <p role="status">Looking for subtitle files…</p>}
      {subtitles.error && <p className="form-error" role="alert">Could not find subtitle files: {subtitles.error}</p>}
      {!subtitles.loading && !subtitles.error && !subtitles.tracks.length && <p data-testid="subtitle-empty">No matching subtitle files found. Use the video's filename with .srt or .vtt, optionally adding a language, such as Movie.en.srt.</p>}
      {subtitles.trackLoading && <p role="status">Loading selected subtitle…</p>}
      {subtitles.trackError && <p role="alert">{subtitles.trackError}</p>}
      {subtitles.selected && <button className="btn" aria-disabled={subtitles.trackLoading}
        onClick={() => { if (!subtitles.trackLoading) subtitles.retry(); }} data-testid="subtitle-track-retry">
        {subtitles.trackLoading ? "Loading subtitle…" : subtitles.trackError ? "Retry selected subtitle" : "Reload selected subtitle"}
      </button>}
      <div className="detail-actions">
        <button className="btn" aria-disabled={subtitles.loading} onClick={() => { if (!subtitles.loading) void subtitles.reload(); }} data-testid="subtitle-refresh">{subtitles.loading ? "Looking…" : "Refresh files"}</button>
        <button className="btn btn--primary" onClick={onClose} data-testid="subtitle-close">Done</button>
      </div>
    </div>
  </div>;
}
