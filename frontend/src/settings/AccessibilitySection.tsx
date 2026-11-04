import { useState } from "react";
import { getMotionPref, setMotionPref, type MotionPref } from "../theme/displayPrefs";
import { setAnnouncementsPref } from "../theme/appearancePrefs";
import { useAnnouncementsPref } from "../theme/useAppearancePrefs";
import { useAnnounce } from "../accessibility/Announcer";
import { Choice, SectionHead, SettingRow } from "./ui";

/** Motion & accessibility (this device). "System" follows the Windows / Xbox setting; "Reduced" always calms motion. */
export function AccessibilitySection() {
  const announcements = useAnnouncementsPref();
  const announce = useAnnounce();
  const [motion, setMotion] = useState<MotionPref>(getMotionPref);
  const system = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const choose = (p: MotionPref) => { setMotionPref(p); setMotion(p); };
  return (
    <div className="ssection" data-testid="settings-accessibility">
      <SectionHead title="Motion & accessibility" intro="Saved on this device only." />
      <SettingRow label="Motion" testId="a11y-motion-row"
        hint={`Reduced removes zooms, slides and smooth scrolling everywhere, including the Atlas and the Filmstrip. Your system setting is currently ${system ? "Reduce motion" : "Full motion"}.`}>
        <Choice testId="a11y-motion" value={motion} onChange={choose}
          options={[{ value: "system", label: "Follow system" }, { value: "reduce", label: "Reduced" }]} />
      </SettingRow>
      <p className="lm-fine" data-testid="a11y-current">Motion is {motion === "reduce" || system ? "reduced" : "full"} on this device.</p>
      <SettingRow testId="a11y-reader-row" label="Additional screen reader announcements"
        hint="Sends page context and action confirmations to your screen reader using ARIA live regions. Requires a running screen reader. Existing control labels, focus feedback and error/status messages remain available when off.">
        <button type="button" className="stoggle" role="switch" aria-label="Additional screen reader announcements" aria-checked={announcements}
          data-testid="a11y-reader" onClick={() => setAnnouncementsPref(!announcements)}>
          <span className="stoggle-track" aria-hidden="true"><span /></span>{announcements ? "On" : "Off"}
        </button>
      </SettingRow>
      <button type="button" className="hbtn" disabled={!announcements} data-testid="a11y-reader-test"
        onClick={() => announce("REELHEIM test announcement. Additional screen reader announcements are enabled.")}>
        Test screen reader announcement
      </button>
      <p className="lm-fine">The test sends a live-region message without moving focus. Your screen reader controls how it is spoken.</p>
    </div>
  );
}
