/**
 * Spatial (directional) navigation for keyboard, TV remotes and game controllers.
 * Arrow keys / D-pad move focus to the nearest focusable element in that direction.
 * Enter / A activates; Escape / Backspace / B goes back.
 */
type Dir = "up" | "down" | "left" | "right";

const FOCUSABLE = 'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), [data-nav]';
const KEY_DIR: Record<string, Dir> = { ArrowUp: "up", ArrowDown: "down", ArrowLeft: "left", ArrowRight: "right" };

type BackHandler = () => boolean | void;
const backStack: BackHandler[] = [];
let fallbackBack: () => void = () => window.history.back();

export function pushBackHandler(fn: BackHandler): () => void {
  backStack.push(fn);
  return () => {
    const i = backStack.lastIndexOf(fn);
    if (i >= 0) backStack.splice(i, 1);
  };
}

export function setFallbackBack(fn: () => void) {
  fallbackBack = fn;
}

export function goBack() {
  for (let i = backStack.length - 1; i >= 0; i--) {
    if (backStack[i]() !== false) return;
  }
  fallbackBack();
}

function scopeRoot(): ParentNode {
  const scopes = document.querySelectorAll('[data-nav-scope="modal"]');
  return scopes.length ? scopes[scopes.length - 1] : document;
}

function visible(el: Element): boolean {
  const r = el.getBoundingClientRect();
  if (r.width === 0 && r.height === 0) return false;
  const style = getComputedStyle(el);
  return style.visibility !== "hidden" && style.display !== "none";
}

export function focusables(): HTMLElement[] {
  return Array.from(scopeRoot().querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
    (el) => !el.closest("[data-nav-skip]") && visible(el)
  );
}

export function focusFirst(container?: Element | null) {
  const root = container ?? scopeRoot();
  const preferred = root.querySelector<HTMLElement>("[data-autofocus]");
  const target = preferred && visible(preferred) ? preferred : focusables().find((el) => root.contains(el));
  target?.focus({ preventScroll: false });
}

function pickNext(from: HTMLElement, dir: Dir): HTMLElement | null {
  // Inside a horizontal rail (data-nav-row), Left/Right stay in the rail and stop at its edges (no wrap, no jump out).
  const row = dir === "left" || dir === "right" ? from.closest("[data-nav-row]") : null;
  const a = from.getBoundingClientRect();
  const ax = a.left + a.width / 2;
  const ay = a.top + a.height / 2;
  let best: HTMLElement | null = null;
  let bestScore = Infinity;
  for (const el of focusables()) {
    if (el === from || (row && !row.contains(el))) continue;
    const b = el.getBoundingClientRect();
    const bx = b.left + b.width / 2;
    const by = b.top + b.height / 2;
    const EDGE = 8; // candidates must lie beyond the current element's edge in the travel direction
    let primary: number;
    let secondary: number;
    switch (dir) {
      case "right": if (b.left < a.right - EDGE) continue; primary = b.left - a.right; secondary = Math.abs(by - ay); break;
      case "left": if (b.right > a.left + EDGE) continue; primary = a.left - b.right; secondary = Math.abs(by - ay); break;
      case "down": if (b.top < a.bottom - EDGE) continue; primary = b.top - a.bottom; secondary = Math.abs(bx - ax); break;
      default: if (b.bottom > a.top + EDGE) continue; primary = a.top - b.bottom; secondary = Math.abs(bx - ax);
    }
    // Rows: strongly prefer the same line. Columns: allow reasonable sideways offset (e.g. tabs -> buttons above).
    const score = Math.max(0, primary) + secondary * (dir === "left" || dir === "right" ? 2.5 : 1.2);
    if (score < bestScore) {
      bestScore = score;
      best = el;
    }
  }
  // Entering a tab list from outside lands on its selected tab, so passing through never switches groups by accident.
  const tabs = best?.closest("[data-nav-prefer-selected]");
  if (best && tabs && !tabs.contains(from)) {
    const sel = tabs.querySelector<HTMLElement>('[aria-selected="true"], [aria-current="true"]');
    if (sel && visible(sel)) return sel;
  }
  return best;
}

export function move(dir: Dir): boolean {
  const active = document.activeElement as HTMLElement | null;
  const list = focusables();
  if (!active || active === document.body || !list.includes(active)) {
    const modal = document.querySelector('[data-nav-scope="modal"]');
    focusFirst(modal ? null : document.querySelector("main"));
    return true;
  }
  // Regions can name an explicit Up target (e.g. the Filmstrip header -> the Stage action) to avoid jumping to the top nav.
  // ...and an explicit Down target (detail actions -> the selected season tab).
  const upSel = dir === "up" ? active.closest<HTMLElement>("[data-nav-up]")?.dataset.navUp
    : dir === "down" ? active.closest<HTMLElement>("[data-nav-down]")?.dataset.navDown : undefined;
  const upTarget = upSel ? document.querySelector<HTMLElement>(upSel) : null;
  if (upTarget && visible(upTarget)) {
    upTarget.focus({ preventScroll: true });
    upTarget.scrollIntoView({ block: "nearest", behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
    return true;
  }
  const next = pickNext(active, dir);
  if (!next && active.closest("[data-nav-row]") && (dir === "left" || dir === "right")) {
    active.classList.remove("nav-edge");
    void active.offsetWidth;
    active.classList.add("nav-edge");
    return true;
  }
  if (next) {
    next.focus({ preventScroll: true });
    // Containers marked data-nav-noscroll (the Filmstrip) position their own content.
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (next.closest("[data-nav-noscroll]")) next.closest("section, main")?.scrollIntoView({ block: "nearest", behavior: reduce ? "auto" : "smooth" });
    else next.scrollIntoView({ block: "nearest", inline: "nearest", behavior: reduce ? "auto" : "smooth" });
    return true;
  }
  return false;
}

function isTextInput(el: Element | null): el is HTMLInputElement {
  return el instanceof HTMLInputElement && !["button", "checkbox", "radio", "range"].includes(el.type);
}

function onKeyDown(e: KeyboardEvent) {
  if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey) return;
  document.body.dataset.input = "keys";
  const dir = KEY_DIR[e.key];
  const active = document.activeElement;
  if (dir) {
    if (isTextInput(active) && (dir === "left" || dir === "right")) {
      const atStart = active.selectionStart === 0 && active.selectionEnd === 0;
      const atEnd = active.selectionStart === active.value.length;
      if (!((dir === "left" && atStart) || (dir === "right" && atEnd))) return;
    }
    if (move(dir)) e.preventDefault();
    return;
  }
  if (e.key === "Escape" || e.key === "GoBack" || e.key === "BrowserBack" || (e.key === "Backspace" && !isTextInput(active))) {
    e.preventDefault();
    goBack();
  }
}

/* Gamepad API polling (Xbox / XInput standard mapping). */
const PAD_DIR: Record<number, Dir> = { 12: "up", 13: "down", 14: "left", 15: "right" };
const REPEAT_DELAY = 380;
const REPEAT_RATE = 110;
const held: Record<string, number> = {};
let rafId = 0;

function dispatchKey(key: string) {
  const target = document.activeElement ?? document.body;
  const ev = new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true });
  target.dispatchEvent(ev);
}

function pressed(id: string, isDown: boolean, now: number, fire: () => void, repeat: boolean) {
  if (!isDown) {
    delete held[id];
    return;
  }
  const t = held[id];
  if (t === undefined) {
    held[id] = now + REPEAT_DELAY;
    fire();
  } else if (repeat && now >= t) {
    held[id] = now + REPEAT_RATE;
    fire();
  }
}

function pollGamepads() {
  const now = performance.now();
  for (const pad of navigator.getGamepads?.() ?? []) {
    if (!pad) continue;
    const ax = pad.axes[0] ?? 0;
    const ay = pad.axes[1] ?? 0;
    const stick: Record<Dir, boolean> = { left: ax < -0.6, right: ax > 0.6, up: ay < -0.6, down: ay > 0.6 };
    for (const [btn, dir] of Object.entries(PAD_DIR)) {
      const down = !!pad.buttons[Number(btn)]?.pressed || stick[dir];
      const key = { up: "ArrowUp", down: "ArrowDown", left: "ArrowLeft", right: "ArrowRight" }[dir];
      pressed(`${pad.index}-${dir}`, down, now, () => { document.body.dataset.input = "pad"; dispatchKey(key); }, true);
    }
    pressed(`${pad.index}-a`, !!pad.buttons[0]?.pressed, now, () => {
      document.body.dataset.input = "pad";
      const el = document.activeElement as HTMLElement | null;
      if (el instanceof HTMLButtonElement || el instanceof HTMLAnchorElement) el.click();
      else dispatchKey("Enter");
    }, false);
    pressed(`${pad.index}-b`, !!pad.buttons[1]?.pressed, now, () => dispatchKey("Escape"), false);
    pressed(`${pad.index}-x`, !!pad.buttons[2]?.pressed, now, () => dispatchKey("PadX"), true);
    pressed(`${pad.index}-y`, !!pad.buttons[3]?.pressed, now, () => dispatchKey("PadY"), false);
    pressed(`${pad.index}-lb`, !!pad.buttons[4]?.pressed, now, () => dispatchKey("PageUp"), false);
    pressed(`${pad.index}-rb`, !!pad.buttons[5]?.pressed, now, () => dispatchKey("PageDown"), false);
    pressed(`${pad.index}-play`, !!pad.buttons[9]?.pressed, now, () => dispatchKey("MediaPlayPause"), false);
  }
  rafId = requestAnimationFrame(pollGamepads);
}

export function installNavigation(): () => void {
  window.addEventListener("keydown", onKeyDown);
  const onPointer = () => { document.body.dataset.input = "mouse"; };
  window.addEventListener("pointerdown", onPointer);
  window.addEventListener("pointermove", onPointer);
  rafId = requestAnimationFrame(pollGamepads);
  return () => {
    window.removeEventListener("keydown", onKeyDown);
    window.removeEventListener("pointerdown", onPointer);
    window.removeEventListener("pointermove", onPointer);
    cancelAnimationFrame(rafId);
  };
}
