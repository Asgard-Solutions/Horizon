// Device-local display preferences (this screen only): motion and UI size. Playback preferences live on the server.
import { applyUiScale } from "./uiScale";
import { startAppearancePrefs } from "./appearancePrefs";

const MOTION_KEY = "horizon.motion";
export type MotionPref = "system" | "reduce";

export const getMotionPref = (): MotionPref => (localStorage.getItem(MOTION_KEY) === "reduce" ? "reduce" : "system");

/** True when either this device's setting or the operating system asks for reduced motion. */
export function reducedMotion(): boolean {
  return getMotionPref() === "reduce" || window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function applyMotion() {
  document.documentElement.dataset.motion = getMotionPref() === "reduce" ? "reduce" : "system";
}

export function setMotionPref(p: MotionPref) {
  localStorage.setItem(MOTION_KEY, p);
  applyMotion();
}

export function startDisplayPrefs() {
  startAppearancePrefs();
  applyMotion();
  applyUiScale();
}
