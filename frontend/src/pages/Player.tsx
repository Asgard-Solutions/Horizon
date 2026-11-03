import { Loader2, Pause, Play } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api, mediaUrl, saveProgress } from "../api";
import { ErrorState, Loading } from "../components/States";
import { useAsync, useBack } from "../hooks";
import { PlayerControls, type ControlsMode, type ControlsState } from "../player/Controls";
import { mediaErrorMessage, ProblemPanel, ResumePrompt } from "../player/Panels";
import type { PlaybackInfo } from "../types";

type Phase = "blocked" | "resume" | "starting" | "ready" | "error";
type Flash = { n: number; kind: "play" | "pause" | "back" | "fwd" };
const NATIVE_CONTAINERS = ["mp4", "m4v", "mov", "webm"];
const HIDE_AFTER_MS = 4000;
const START_TIMEOUT_MS = 30000;
const BACK_KEYS = ["Escape", "Backspace", "GoBack", "BrowserBack"];

function clientCheck(info: PlaybackInfo): string[] {
  const c = info.compatibility;
  if (c.status === "unsupported") return c.reasons;
  if (!NATIVE_CONTAINERS.includes(info.container)) return [];
  const type = c.codecs ? `${c.mime}; codecs="${c.codecs}"` : c.mime;
  const answer = document.createElement("video").canPlayType(type);
  return answer ? [] : [`This browser reports it cannot play "${type}".`, ...c.reasons];
}

function FlashMark({ flash }: { flash: Flash }) {
  return (
    <div className="pc-flash" data-kind={flash.kind} data-testid="player-flash" aria-hidden="true">
      {flash.kind === "play" ? <Play size={44} fill="currentColor" /> : flash.kind === "pause" ? <Pause size={44} fill="currentColor" />
        : <span>{flash.kind === "back" ? "−10" : "+10"}</span>}
    </div>
  );
}

export default function Player() {
  const { fileId } = useParams();
  const [search] = useSearchParams();
  const navigate = useNavigate();
  const { data: info, error, reload } = useAsync(() => api<PlaybackInfo>(`/api/files/${fileId}/playback`), [fileId]);

  const videoRef = useRef<HTMLVideoElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const playRef = useRef<HTMLButtonElement>(null);
  const hideTimer = useRef<number>(0);
  const flashN = useRef(0);
  const [phase, setPhase] = useState<Phase>("starting");
  const [reasons, setReasons] = useState<string[]>([]);
  const [startAt, setStartAt] = useState<number | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [mode, setMode] = useState<ControlsMode>("osd");
  const modeRef = useRef(mode);
  modeRef.current = mode;
  const [flash, setFlash] = useState<Flash | null>(null);
  const [s, setS] = useState<ControlsState>({
    playing: false, time: 0, duration: 0, buffered: 0,
    volume: Number(localStorage.getItem("mc-volume") ?? 1), muted: false, fullscreen: false,
  });

  useEffect(() => {
    if (!info) return;
    setWarning(null);
    const problems = clientCheck(info);
    if (problems.length) {
      setReasons(problems);
      setPhase("blocked");
      return;
    }
    const qs = search.get("start");
    if (qs !== null) return void (setStartAt(Number(qs) || 0), setPhase("starting"));
    const p = info.progress;
    if (p && !p.watched && p.position > 10) setPhase("resume");
    else (setStartAt(0), setPhase("starting"));
  }, [info, search]);

  const persist = useCallback(() => {
    const v = videoRef.current;
    if (v && info && v.currentTime > 0) saveProgress(info.file_id, v.currentTime, isFinite(v.duration) ? v.duration : null);
  }, [info]);

  const exit = useCallback(() => {
    persist();
    if (document.fullscreenElement) document.exitFullscreen().catch(() => undefined);
    // Return to wherever playback was started from (Home, details...); deep links fall back to the item's page.
    const idx = (window.history.state as { idx?: number } | null)?.idx ?? 0;
    if (idx > 0) navigate(-1);
    else navigate(info?.context.back ?? "/", { replace: true });
  }, [persist, navigate, info]);
  useBack(() => exit());

  const surface = () => stageRef.current?.focus({ preventScroll: true });
  // Controls fade ~4 s after the last interaction, but only while playing; paused keeps them on screen.
  const arm = useCallback(() => {
    window.clearTimeout(hideTimer.current);
    hideTimer.current = window.setTimeout(() => {
      if (videoRef.current && !videoRef.current.paused) {
        setMode("hidden");
        stageRef.current?.focus({ preventScroll: true });
      }
    }, HIDE_AFTER_MS);
  }, []);
  const reveal = useCallback(() => { setMode((m) => (m === "hidden" ? "osd" : m)); arm(); }, [arm]);
  const expand = useCallback(() => {
    setMode("expanded");
    arm();
    window.setTimeout(() => playRef.current?.focus({ preventScroll: true }), 0);
  }, [arm]);
  const collapse = useCallback(() => {
    setMode(videoRef.current?.paused ? "osd" : "hidden");
    surface();
    arm();
  }, [arm]);
  // B / Esc closes the expanded controls first; the next Back leaves the player.
  useBack(() => collapse(), mode === "expanded");
  const flashIt = (kind: Flash["kind"]) => setFlash({ n: ++flashN.current, kind });
  useEffect(() => {
    if (!flash) return;
    const t = window.setTimeout(() => setFlash(null), 700);
    return () => window.clearTimeout(t);
  }, [flash]);

  const toggle = useCallback(() => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) { v.play().catch(() => undefined); flashIt("play"); }
    else { v.pause(); flashIt("pause"); }
    reveal();
  }, [reveal]);
  const seekTo = useCallback((t: number) => {
    const v = videoRef.current;
    if (!v || !isFinite(v.duration)) return;
    v.currentTime = Math.max(0, Math.min(v.duration - 0.5, t));
    reveal();
  }, [reveal]);
  const seekBy = useCallback((d: number) => {
    flashIt(d < 0 ? "back" : "fwd");
    seekTo((videoRef.current?.currentTime ?? 0) + d);
  }, [seekTo]);
  const volumeBy = useCallback((d: number) => {
    const v = videoRef.current;
    if (!v) return;
    v.muted = false;
    v.volume = Math.max(0, Math.min(1, Math.round((v.volume + d) * 10) / 10));
    reveal();
  }, [reveal]);
  const mute = useCallback(() => { if (videoRef.current) videoRef.current.muted = !videoRef.current.muted; reveal(); }, [reveal]);
  const fullscreen = useCallback(() => {
    if (document.fullscreenElement) document.exitFullscreen().catch(() => undefined);
    else stageRef.current?.requestFullscreen().catch(() => undefined);
    reveal();
  }, [reveal]);

  // Start the stream once a start position is known.
  useEffect(() => {
    const v = videoRef.current;
    if (phase !== "starting" || !v || !info || startAt === null) return;
    v.src = mediaUrl(info.stream_url)!;
    v.volume = s.volume;
    const timer = window.setTimeout(() => {
      if (v.readyState < 1) {
        setReasons(["The video did not start within 30 seconds. The file may be unreachable or in an unsupported format."]);
        setPhase("error");
      }
    }, START_TIMEOUT_MS);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, info, startAt]);

  // Save progress periodically and on leave.
  useEffect(() => {
    if (phase !== "ready") return;
    const t = window.setInterval(() => { if (videoRef.current && !videoRef.current.paused) persist(); }, 10000);
    const onHide = () => persist();
    window.addEventListener("pagehide", onHide);
    return () => { window.clearInterval(t); window.removeEventListener("pagehide", onHide); persist(); };
  }, [phase, persist]);

  useEffect(() => {
    const onFs = () => setS((x) => ({ ...x, fullscreen: !!document.fullscreenElement }));
    document.addEventListener("fullscreenchange", onFs);
    return () => document.removeEventListener("fullscreenchange", onFs);
  }, []);

  // Player keys run in the capture phase, before spatial navigation. On the playback surface (controls not expanded)
  // A/Enter toggles, Left/Right seek 10 s, Up expands. Once expanded, arrows only move focus between controls.
  useEffect(() => {
    if (phase !== "ready" && phase !== "starting") return;
    const onKey = (e: KeyboardEvent) => {
      if (BACK_KEYS.includes(e.key) || e.altKey || e.ctrlKey || e.metaKey) return;
      const stop = () => { e.preventDefault(); e.stopPropagation(); };
      const key = e.key.toLowerCase();
      if (key === " " || key === "k" || e.key === "MediaPlayPause") return void (stop(), toggle());
      if (key === "f") return void (stop(), fullscreen());
      if (key === "m") return void (stop(), mute());
      if (modeRef.current !== "expanded") {
        if (e.key === "ArrowLeft") return void (stop(), seekBy(-10));
        if (e.key === "ArrowRight") return void (stop(), seekBy(10));
        if (e.key === "Enter") return void (stop(), toggle());
        if (e.key === "ArrowUp") return void (stop(), expand());
        if (e.key === "ArrowDown") return void (stop(), reveal());
        return;
      }
      arm();
      const active = document.activeElement as HTMLElement | null;
      if (!active?.closest(".pc") && e.key.startsWith("Arrow")) return void (stop(), playRef.current?.focus({ preventScroll: true }));
      if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
      if (active?.dataset.seekbar !== undefined) return void (stop(), seekBy(e.key === "ArrowLeft" ? -10 : 10));
      if (active?.dataset.volume !== undefined) return void (stop(), volumeBy(e.key === "ArrowLeft" ? -0.1 : 0.1));
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [phase, toggle, fullscreen, mute, seekBy, volumeBy, expand, reveal, arm]);

  useEffect(() => () => window.clearTimeout(hideTimer.current), []);
  useEffect(() => {
    if (phase === "ready") window.setTimeout(surface, 0);
  }, [phase]);

  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!info) return <Loading label="Preparing playback" />;
  const ctx = info.context;
  const update = () => {
    const v = videoRef.current!;
    const end = v.buffered.length ? v.buffered.end(v.buffered.length - 1) : 0;
    setS((x) => ({ ...x, time: v.currentTime, duration: isFinite(v.duration) ? v.duration : 0, buffered: end,
      playing: !v.paused, volume: v.volume, muted: v.muted }));
  };

  return (
    <div className="player" ref={stageRef} tabIndex={-1} data-mode={mode} data-testid="player-page" data-phase={phase}
      onMouseMove={() => { if (modeRef.current !== "expanded") setMode("expanded"); arm(); }}>
      <video
        ref={videoRef}
        className="player-video"
        playsInline
        preload="metadata"
        data-testid="player-video"
        onClick={toggle}
        onDoubleClick={fullscreen}
        onLoadedMetadata={(e) => {
          const v = e.currentTarget;
          if (startAt) v.currentTime = Math.min(startAt, Math.max(0, v.duration - 1));
          if (v.videoWidth === 0 && info.probe?.video?.length)
            setWarning(`The video track (${info.probe.video[0].codec}) could not be decoded by this browser — only audio may play.`);
          v.play().catch(() => setPhase("ready"));
          update();
        }}
        onPlaying={() => { setPhase("ready"); arm(); update(); }}
        onPause={() => { update(); persist(); setMode((m) => (m === "hidden" ? "osd" : m)); }}
        onTimeUpdate={update}
        onProgress={update}
        onVolumeChange={(e) => { localStorage.setItem("mc-volume", String(e.currentTarget.volume)); update(); }}
        onEnded={() => { update(); persist(); expand(); }}
        onError={(e) => { setReasons([mediaErrorMessage(e.currentTarget.error), ...info.compatibility.reasons]); setPhase("error"); }}
      />
      {phase === "starting" && startAt !== null && (
        <div className="player-loading" data-testid="player-starting"><Loader2 className="spin" size={54} /><span>Starting playback…</span></div>
      )}
      {phase === "resume" && info.progress && (
        <ResumePrompt position={info.progress.position}
          onResume={() => { setStartAt(info.progress!.position); setPhase("starting"); }}
          onRestart={() => { setStartAt(0); setPhase("starting"); }} />
      )}
      {phase === "blocked" && (
        <ProblemPanel info={info} title="This file can't be played here" reasons={reasons} onBack={exit}
          onTryAnyway={() => { setStartAt(0); setPhase("starting"); }} testId="unsupported-panel" />
      )}
      {phase === "error" && (
        <ProblemPanel info={info} title="Playback failed" reasons={reasons} onBack={exit} testId="playback-error-panel" />
      )}
      {warning && phase === "ready" && <div className="player-warning" role="status" data-testid="player-warning">{warning}</div>}
      {phase === "ready" && flash && <FlashMark key={flash.n} flash={flash} />}
      {phase === "ready" && (
        <PlayerControls s={s} mode={mode} eyebrow={ctx.kind === "movie" ? "Now playing · Movie" : "Now playing · Episode"}
          title={ctx.title ?? info.filename} subtitle={ctx.subtitle}
          hasNext={!!ctx.next_file_id} playRef={playRef} onToggle={toggle} onSeekBy={seekBy} onSeekTo={seekTo}
          onVolumeBy={volumeBy} onMute={mute} onFullscreen={fullscreen} onExit={exit}
          onNext={() => { persist(); setMode("osd"); navigate(`/play/${ctx.next_file_id}?start=0`, { replace: true }); }} />
      )}
    </div>
  );
}
