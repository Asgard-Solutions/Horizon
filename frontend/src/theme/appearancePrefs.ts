// REELHEIM has one appearance. Announcements remain device-local, separate from motion and size.
const CHANGE = "horizon-appearance";
const KEYS = ["horizon.announcements"];
const temporary = new Map<string, string>();

function read(key: string): string | null {
  if (temporary.has(key)) return temporary.get(key)!;
  try { return localStorage.getItem(key); } catch { return null; }
}
export const getAnnouncementsPref = () => read(KEYS[0]) === "true";

export function applyAppearancePrefs() {
  const root = document.documentElement;
  // Ignore retired saved choices, including values set by an older open tab.
  root.dataset.theme = "dark";
  root.dataset.contrast = "normal";
  root.dataset.announcements = getAnnouncementsPref() ? "on" : "off";
  root.style.colorScheme = "dark";
}

function save(key: string, value: string) {
  if (read(key) === value) return;
  try { localStorage.setItem(key, value); temporary.delete(key); }
  catch { temporary.set(key, value); } // Still usable for this session when browser storage is blocked.
  applyAppearancePrefs();
  window.dispatchEvent(new Event(CHANGE));
}
export const setAnnouncementsPref = (value: boolean) => save(KEYS[0], String(value === true));
export function subscribeAppearancePrefs(onChange: () => void) {
  window.addEventListener(CHANGE, onChange);
  return () => window.removeEventListener(CHANGE, onChange);
}

export function startAppearancePrefs() {
  applyAppearancePrefs();
  const sync = (event: StorageEvent) => {
    if (event.key !== null && !KEYS.includes(event.key)) return;
    if (event.key === null) temporary.clear(); else temporary.delete(event.key);
    applyAppearancePrefs();
    window.dispatchEvent(new Event(CHANGE));
  };
  window.addEventListener("storage", sync);
  return () => window.removeEventListener("storage", sync);
}
