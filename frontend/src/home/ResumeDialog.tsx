import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { formatTime } from "../format";
import { useBack } from "../hooks";
import type { ContinueItem, PlaybackInfo } from "../types";
import { scopedPath, type MediaType } from "./context";

export function ResumeDialog({ item, type, onClose }: { item: ContinueItem; type: MediaType; onClose: () => void }) {
  const navigate = useNavigate();
  const [info, setInfo] = useState<PlaybackInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const box = useRef<HTMLDivElement>(null);
  const opener = useRef(document.activeElement as HTMLElement | null);
  useBack(() => { onClose(); return true; });
  useEffect(() => {
    const controller = new AbortController();
    box.current?.querySelector<HTMLButtonElement>("[data-close]")?.focus();
    api<PlaybackInfo>(`/api/files/${item.file_id}/playback`, { signal: controller.signal })
      .then(async value => {
        await api<null>(value.stream_url, { method: "HEAD", signal: controller.signal });
        if (controller.signal.aborted) return;
        setInfo(value);
      }).catch((failure: Error) => { if (!controller.signal.aborted) setError(failure.message); });
    return () => { controller.abort(); if (opener.current?.isConnected) opener.current.focus({ preventScroll: true }); };
  }, [item.file_id]);
  useEffect(() => {
    if (info && document.activeElement?.hasAttribute("data-close")) box.current?.querySelector<HTMLButtonElement>("[data-resume]:not([disabled])")?.focus();
  }, [info]);
  const progress = info?.progress;
  const resumable = !!progress && !progress.watched && progress.position > 0 && progress.duration !== null && progress.position < progress.duration;
  const title = item.type === "movie" ? item.title : item.show_title;
  const play = (position: number) => navigate(scopedPath(`/play/${item.file_id}?start=${Math.floor(position)}`, type));
  const trap = (event: KeyboardEvent) => {
    if (event.key !== "Tab") return;
    const controls = [...box.current!.querySelectorAll<HTMLButtonElement>("button:not([disabled])")];
    const current = controls.indexOf(document.activeElement as HTMLButtonElement);
    event.preventDefault();
    controls[(current + (event.shiftKey ? -1 : 1) + controls.length) % controls.length]?.focus();
  };
  return (
    <div className="hub-modal-backdrop" data-nav-scope="modal" onKeyDown={trap}>
      <div className="hub-modal" ref={box} role="dialog" aria-modal="true" aria-labelledby="resume-title" aria-describedby="resume-status" data-testid="resume-dialog">
        <h2 id="resume-title">{title}</h2>
        <p id="resume-status" role={error ? "alert" : "status"}>
          {error ? `This media file is unavailable. ${error}` : !info ? "Checking this media file…"
            : resumable ? `Resume from ${formatTime(progress!.position)}, or start over.` : "No unfinished position is currently saved. You can start from the beginning."}
        </p>
        <div className="hub-modal-actions">
          {info && <>
            <button className="hub-action" data-resume disabled={!resumable} onClick={() => play(progress!.position)} data-testid="hub-resume">Resume</button>
            <button className="hub-action" onClick={() => play(0)} data-testid="hub-start-over">Start Over</button>
          </>}
          {error && <button className="hub-action" data-testid="resume-library-settings" onClick={() => navigate(scopedPath("/settings?section=libraries", type))}>Library Settings</button>}
          <button className="hub-action" data-close onClick={onClose} data-testid="hub-resume-close">{error ? "Close" : "Cancel"}</button>
        </div>
      </div>
    </div>
  );
}
