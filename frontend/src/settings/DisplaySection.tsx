import { useEffect, useState } from "react";
import { autoScale, getScalePref, SCALE_OPTIONS, setScalePref, zoomSupported, type ScalePref } from "../theme/uiScale";
import { Choice, ComingLater, SectionHead, SettingRow } from "./ui";

const LABEL: Record<ScalePref, string> = { auto: "Auto", "1": "100%", "1.25": "125%", "1.5": "150%", "1.75": "175%", "2": "200%" };

function useViewport() {
  const read = () => ({ w: window.innerWidth, h: window.innerHeight, dpr: window.devicePixelRatio, zoom: document.documentElement.dataset.uiScale ?? "1" });
  const [v, setV] = useState(read);
  useEffect(() => {
    const on = () => setV(read());
    window.addEventListener("resize", on);
    window.addEventListener("horizon-ui-scale", on);
    return () => { window.removeEventListener("resize", on); window.removeEventListener("horizon-ui-scale", on); };
  }, []);
  return v;
}

/** Appearance & 4K scaling. Saved on this device only (a TV and a desk monitor usually want different sizes). */
export function DisplaySection() {
  const [pref, setPref] = useState<ScalePref>(getScalePref);
  const v = useViewport();
  const supported = zoomSupported();
  const choose = (p: ScalePref) => { setScalePref(p); setPref(p); };
  const auto = Math.round(autoScale() * 100);
  return (
    <div className="ssection" data-testid="settings-display">
      <SectionHead title="Appearance & 4K scaling" intro="Saved on this device only." />
      <SettingRow label="Interface size" testId="display-scale-row"
        hint={supported
          ? `Auto fits Horizon's 1080p layout to this screen (currently ${auto}%). It never adds to Windows display scaling, which this browser already applies.`
          : "This browser cannot zoom the interface, so Horizon stays at 100%. Use the browser's own zoom (Ctrl + / Ctrl -) instead."}>
        <Choice testId="display-scale" value={pref} onChange={choose} disabled={!supported}
          options={SCALE_OPTIONS.map((o) => ({ value: o, label: LABEL[o] }))} />
      </SettingRow>
      <dl className="sfacts" data-testid="display-facts">
        <dt>Applied size</dt><dd data-testid="display-applied">{Math.round(Number(v.zoom) * 100)}%{pref === "auto" ? " (Auto)" : " (manual)"}</dd>
        <dt>Browser window</dt><dd data-testid="display-viewport">{v.w} × {v.h} CSS pixels</dd>
        <dt>Display scaling</dt><dd data-testid="display-dpr">{Math.round(v.dpr * 100)}% (set by Windows / the console)</dd>
      </dl>
      {pref !== "auto" && v.w / Number(pref) < 1280 && (
        <p className="lm-note" data-testid="display-scale-warning">At this size the screen is narrower than Horizon's smallest layout; some rows may scroll sideways.</p>
      )}
      {pref !== "auto" && <button className="hbtn hbtn--quiet" onClick={() => choose("auto")} data-testid="display-scale-reset">Reset to Auto</button>}
      <ComingLater testId="display-theme-later" label="Light theme" hint="Horizon currently uses its dark Obsidian theme only." />
    </div>
  );
}
