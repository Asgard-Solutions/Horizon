import { api } from "../api";
import { useAsync } from "../hooks";
import type { Preferences } from "../types";
import { Choice, ComingLater, SectionHead, SettingRow, Toggle } from "./ui";

export const PREF_DEFAULTS: Preferences = { resume: "ask", autoplay_next: false, skip_seconds: 10, watched_threshold: "95" };
export const loadPreferences = () => api<Preferences>("/api/preferences").catch(() => PREF_DEFAULTS);

/** Playback preferences are saved on the host and apply on every screen (this PC and paired devices). */
export function PlaybackSection() {
  const { data, setData } = useAsync(loadPreferences, []);
  if (!data) return null;
  const save = (p: Partial<Preferences>) => {
    setData({ ...data, ...p });
    api<Preferences>("/api/preferences", { method: "PUT", body: JSON.stringify(p) }).then(setData).catch(() => setData(data));
  };
  return (
    <div className="ssection" data-testid="settings-playback">
      <SectionHead title="Playback" intro="Saved on the host, so they apply on this PC and on paired devices such as the Xbox." />
      <SettingRow label="Resume" testId="pref-resume-row"
        hint="Ask shows Resume / Start over. Automatic continues where you stopped and offers Start over for a few seconds.">
        <Choice testId="pref-resume" value={data.resume} onChange={(v) => save({ resume: v })}
          options={[{ value: "ask", label: "Ask each time" }, { value: "auto", label: "Resume automatically" }]} />
      </SettingRow>
      <SettingRow label="Auto-play next episode" testId="pref-autoplay-row"
        hint="When an episode ends, the next one starts after a 10-second countdown you can cancel.">
        <Toggle on={data.autoplay_next} onChange={(v) => save({ autoplay_next: v })} testId="pref-autoplay" />
      </SettingRow>
      <SettingRow label="Skip step" testId="pref-skip-row" hint="How far Left / Right (D-pad or keyboard) and the skip buttons jump.">
        <Choice testId="pref-skip" value={data.skip_seconds} onChange={(v) => save({ skip_seconds: v })}
          options={[{ value: 10, label: "10 s" }, { value: 30, label: "30 s" }, { value: 60, label: "60 s" }]} />
      </SettingRow>
      <SettingRow label="Mark as watched at" testId="pref-watched-row"
        hint="Applies to movies and episodes from now on. Titles already marked watched stay watched.">
        <Choice testId="pref-watched" value={data.watched_threshold} onChange={(v) => save({ watched_threshold: v })}
          options={[{ value: "90", label: "90%" }, { value: "95", label: "95%" }, { value: "end", label: "The end" }]} />
      </SettingRow>
      <ComingLater testId="pref-subtitles-later" label="Local subtitle files" hint="Subtitles stored next to the video (.srt / .vtt). Not available yet." />
    </div>
  );
}
