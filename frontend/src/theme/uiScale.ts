// The 10-foot layout is designed on a 1920x1080 canvas. Browsers that report a much larger CSS viewport
// (a 4K TV at 100% Windows scaling) get the same layout zoomed up, so text and focus stay readable from the couch.
// Xbox Edge and Windows at its default TV scaling already report ~1080p CSS pixels and are left at 1x.
// Auto never double-scales: CSS pixels already include the operating system's display scaling (devicePixelRatio).
// A manual size (100-200%) saved on this device overrides Auto.
const BASE_W = 1920;
const BASE_H = 1080;
const MIN_ZOOM = 1.25;
const KEY = "horizon.uiScale";
export const SCALE_OPTIONS = ["auto", "1", "1.25", "1.5", "1.75", "2"] as const;
export type ScalePref = (typeof SCALE_OPTIONS)[number];

export const zoomSupported = () => typeof CSS !== "undefined" && CSS.supports("zoom", "2");
export const getScalePref = (): ScalePref => {
  const v = localStorage.getItem(KEY) as ScalePref | null;
  return v && SCALE_OPTIONS.includes(v) ? v : "auto";
};

export function autoScale(): number {
  const fit = Math.min(window.innerWidth / BASE_W, window.innerHeight / BASE_H);
  return fit >= MIN_ZOOM ? Math.round(fit * 100) / 100 : 1;
}

export function applyUiScale() {
  const root = document.documentElement;
  const pref = getScalePref();
  const zoom = !zoomSupported() ? 1 : pref === "auto" ? autoScale() : Number(pref);
  root.style.setProperty("--z", String(zoom));
  root.style.zoom = zoom === 1 ? "" : String(zoom);
  root.dataset.uiScale = String(zoom);
  window.dispatchEvent(new Event("horizon-ui-scale"));
}

export function setScalePref(p: ScalePref) {
  if (p === "auto") localStorage.removeItem(KEY);
  else localStorage.setItem(KEY, p);
  applyUiScale();
}

export function startUiScale() {
  applyUiScale();
  window.addEventListener("resize", () => { if (getScalePref() === "auto") applyUiScale(); });
}
