import { useRef, useState } from "react";
import { api } from "../api";
import { useAsync } from "../hooks";
import type { Preferences } from "../types";
import { Choice, ResourceStatus, SectionHead, SettingRow, Toggle } from "./ui";

export const PREF_DEFAULTS: Preferences = { resume: "ask", autoplay_next: false, skip_seconds: 10, watched_threshold: "95", subtitles: "off" };
export const loadPreferences = () => api<Preferences>("/api/preferences").catch(() => PREF_DEFAULTS);

/** Playback preferences are saved on the host and apply on every screen (this PC and paired devices). */
export function PlaybackSection() {
  const { data, replaceData: setData, loading, error, reload } = useAsync(() => api<Preferences>("/api/preferences"), []);
  const savingRef = useRef(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const save = async (p: Partial<Preferences>) => {
    if (savingRef.current || !data) return;
    savingRef.current = true;
    setSaving(true);
    setSaveError(null);
    setMsg(null);
    try {
      setData(await api<Preferences>("/api/preferences", { method: "PUT", body: JSON.stringify(p) }));
      setMsg("Playback settings saved.");
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Could not save playback settings.");
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  };
  return (
    <div className="ssection" data-testid="settings-playback">
      <SectionHead title="Playback" intro="Saved on the host, so they apply on this PC and on paired devices such as the Xbox." />
      <ResourceStatus loading={loading} error={error} onRetry={reload} testId="playback-load" />
      {data && <>
        <SettingRow label="Resume" testId="pref-resume-row"
          hint="Ask shows Resume / Start over. Automatic continues where you stopped and offers Start over for a few seconds.">
          <Choice testId="pref-resume" value={data.resume} onChange={(v) => save({ resume: v })} busy={saving}
            options={[{ value: "ask", label: "Ask each time" }, { value: "auto", label: "Resume automatically" }]} />
        </SettingRow>
        <SettingRow label="Auto-play next episode" testId="pref-autoplay-row"
          hint="When an episode ends, the next one starts after a 10-second countdown you can cancel.">
          <Toggle on={data.autoplay_next} onChange={(v) => save({ autoplay_next: v })} disabled={saving} testId="pref-autoplay" />
        </SettingRow>
        <SettingRow label="Skip step" testId="pref-skip-row" hint="How far Left / Right (D-pad or keyboard) and the skip buttons jump.">
          <Choice testId="pref-skip" value={data.skip_seconds} onChange={(v) => save({ skip_seconds: v })} busy={saving}
            options={[{ value: 10, label: "10 s" }, { value: 30, label: "30 s" }, { value: 60, label: "60 s" }]} />
        </SettingRow>
        <SettingRow label="Mark as watched at" testId="pref-watched-row"
          hint="Applies to movies and episodes from now on. Titles already marked watched stay watched.">
          <Choice testId="pref-watched" value={data.watched_threshold} onChange={(v) => save({ watched_threshold: v })} busy={saving}
            options={[{ value: "90", label: "90%" }, { value: "95", label: "95%" }, { value: "end", label: "The end" }]} />
        </SettingRow>
        <SettingRow label="Local subtitle files" testId="pref-subtitles-row"
          hint="Finds matching .srt and .vtt files beside each movie or episode, such as Movie.en.srt. Automatic prefers this browser’s language. You can always choose a track or Off from Subtitles in the player.">
          <Choice testId="pref-subtitles" value={data.subtitles ?? "off"} onChange={(v) => save({ subtitles: v })} busy={saving}
            options={[{ value: "off", label: "Off by default" }, { value: "auto", label: "Automatic" }]} />
        </SettingRow>
        {(saving || msg) && <p className="form-hint" role="status" data-testid="playback-save-status">{saving ? "Saving playback settings…" : msg}</p>}
        {saveError && <p className="form-error" role="alert" data-testid="playback-save-error">{saveError}</p>}
      </>}
    </div>
  );
}
