import { Loader2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api, mediaUrl, saveProgress } from "../api";
import { ErrorState, Loading } from "../components/States";
import { useAsync, useBack } from "../hooks";
import { PlayerControls, type ControlsState } from "../player/Controls";
import { mediaErrorMessage, ProblemPanel, ResumePrompt } from "../player/Panels";
import type { PlaybackInfo } from "../types";

type Phase = "blocked" | "resume" | "starting" | "ready" | "error";
const NATIVE_CONTAINERS = ["mp4", "m4v", "mov", "webm"];
const HIDE_AFTER_MS = 4000;
const START_TIMEOUT_MS = 30000;

function clientCheck(info: PlaybackInfo): string[] {
  const c = info.compatibility;
  if (c.status === "unsupported") return c.reasons;
  if (!NATIVE_CONTAINERS.includes(info.container)) return [];
  const type = c.codecs ? `${c.mime}; codecs="${c.codecs}"` : c.mime;
  const answer = document.createElement("video").canPlayType(type);
  return answer ? [] : [`This browser reports it cannot play "${type}".`, ...c.reasons];
}

export default function Player() {
  const { fileId } = useParams();
  const [search] = useSearchParams();
  const navigate = useNavigate();
  const { data: info, error, reload } = useAsync(() => api<PlaybackInfo>(`/api/files/${fileId}/playback`), [fileId]);

  const videoRef = useRef<HTMLVideoElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const seekRef = useRef<HTMLButtonElement>(null);
  const hideTimer = useRef<number>(0);
  const [phase, setPhase] = useState<Phase>("starting");
  const [reasons, setReasons] = useState<string[]>([]);
  const [startAt, setStartAt] = useState<number | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [visible, setVisible] = useState(true);
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
    navigate(info?.context.back ?? "/", { replace: false });
  }, [persist, navigate, info]);
  useBack(() => exit());

  const poke = useCallback(() => {
    setVisible(true);
    window.clearTimeout(hideTimer.current);
    hideTimer.current = window.setTimeout(() => {
      if (videoRef.current && !videoRef.current.paused) {
        setVisible(false);
        seekRef.current?.focus({ preventScroll: true });
      }
    }, HIDE_AFTER_MS);
  }, []);

  const toggle = useCallback(() => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) v.play().catch(() => undefined);
    else v.pause();
    poke();
  }, [poke]);
  const seekTo = useCallback((t: number) => {
    const v = videoRef.current;
    if (!v || !isFinite(v.duration)) return;
    v.currentTime = Math.max(0, Math.min(v.duration - 0.5, t));
    poke();
  }, [poke]);
  const seekBy = useCallback((d: number) => seekTo((videoRef.current?.currentTime ?? 0) + d), [seekTo]);
  const volumeBy = useCallback((d: number) => {
    const v = videoRef.current;
    if (!v) return;
    v.muted = false;
    v.volume = Math.max(0, Math.min(1, Math.round((v.volume + d) * 10) / 10));
    poke();
  }, [poke]);
  const mute = useCallback(() => { if (videoRef.current) videoRef.current.muted = !videoRef.current.muted; poke(); }, [poke]);
  const fullscreen = useCallback(() => {
    if (document.fullscreenElement) document.exitFullscreen().catch(() => undefined);
    else stageRef.current?.requestFullscreen().catch(() => undefined);
    poke();
  }, [poke]);

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

  // Player key handling runs in the capture phase, before global spatial navigation.
  useEffect(() => {
    if (phase !== "ready" && phase !== "starting") return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" || e.key === "Backspace" || e.key === "GoBack") return;
      const active = document.activeElement as HTMLElement | null;
      const stop = () => { e.preventDefault(); e.stopPropagation(); };
      const key = e.key.toLowerCase();
      if (key === " " || key === "k" || e.key === "MediaPlayPause") return void (stop(), toggle());
      if (key === "f") return void (stop(), fullscreen());
      if (key === "m") return void (stop(), mute());
      if (!visible) {
        stop();
        if (e.key === "ArrowLeft") seekBy(-10);
        else if (e.key === "ArrowRight") seekBy(30);
        else if (e.key === "Enter") toggle();
        else { poke(); seekRef.current?.focus(); }
        return;
      }
      poke();
      if (active?.dataset.seekbar !== undefined && (e.key === "ArrowLeft" || e.key === "ArrowRight")) {
        stop();
        seekBy(e.key === "ArrowLeft" ? -10 : 10);
      } else if (active?.dataset.volume !== undefined && (e.key === "ArrowLeft" || e.key === "ArrowRight")) {
        stop();
        volumeBy(e.key === "ArrowLeft" ? -0.1 : 0.1);
      }
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [phase, visible, toggle, fullscreen, mute, seekBy, volumeBy, poke]);

  useEffect(() => () => window.clearTimeout(hideTimer.current), []);
  useEffect(() => {
    if (phase === "ready") window.setTimeout(() => seekRef.current?.focus({ preventScroll: true }), 0);
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
    <div className="player" ref={stageRef} onMouseMove={poke} data-testid="player-page" data-phase={phase}>
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
        onPlaying={() => { setPhase("ready"); poke(); update(); }}
        onPause={() => { update(); persist(); setVisible(true); }}
        onTimeUpdate={update}
        onProgress={update}
        onVolumeChange={(e) => { localStorage.setItem("mc-volume", String(e.currentTarget.volume)); update(); }}
        onEnded={() => { update(); persist(); setVisible(true); }}
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
      {phase === "ready" && (
        <PlayerControls s={s} visible={visible} title={ctx.title ?? info.filename} subtitle={ctx.subtitle}
          hasNext={!!ctx.next_file_id} seekRef={seekRef} onToggle={toggle} onSeekBy={seekBy} onSeekTo={seekTo}
          onVolumeBy={volumeBy} onMute={mute} onFullscreen={fullscreen} onExit={exit}
          onNext={() => { persist(); navigate(`/play/${ctx.next_file_id}?start=0`, { replace: true }); }} />
      )}
    </div>
  );
}
