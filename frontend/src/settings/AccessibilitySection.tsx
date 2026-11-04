import { useState } from "react";
import { getMotionPref, setMotionPref, type MotionPref } from "../theme/displayPrefs";
import { Choice, ComingLater, SectionHead, SettingRow } from "./ui";

/** Motion & accessibility (this device). "System" follows the Windows / Xbox setting; "Reduced" always calms motion. */
export function AccessibilitySection() {
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
      <ComingLater testId="a11y-contrast-later" label="High-contrast mode" hint="Stronger borders and text contrast. Not available yet." />
      <ComingLater testId="a11y-reader-later" label="Screen reader announcements" hint="Spoken focus and status updates. Basic labels exist; a full pass is not done yet." />
    </div>
  );
}
