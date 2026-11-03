// The 10-foot layout is designed on a 1920x1080 canvas. Browsers that report a much larger CSS viewport
// (a 4K TV at 100% Windows scaling) get the same layout zoomed up, so text and focus stay readable from the couch.
// Xbox Edge and Windows at its default TV scaling already report ~1080p CSS pixels and are left at 1x.
const BASE_W = 1920;
const BASE_H = 1080;
const MIN_ZOOM = 1.25;

export function startUiScale() {
  const root = document.documentElement;
  const supported = typeof CSS !== "undefined" && CSS.supports("zoom", "2");
  const update = () => {
    const fit = Math.min(window.innerWidth / BASE_W, window.innerHeight / BASE_H);
    const zoom = supported && fit >= MIN_ZOOM ? Math.round(fit * 100) / 100 : 1;
    root.style.setProperty("--z", String(zoom));
    root.style.zoom = zoom === 1 ? "" : String(zoom);
    root.dataset.uiScale = String(zoom);
  };
  update();
  window.addEventListener("resize", update);
}
