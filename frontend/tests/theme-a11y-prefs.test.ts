import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";

// A disposable screen/storage boundary: these tests never open the app or touch real preferences.
const values = new Map<string, string>();
const root = { dataset: {} as Record<string, string>, style: { colorScheme: "" } };
let prefs: typeof import("../src/theme/appearancePrefs.ts");
let restore: (() => void)[] = [];
beforeEach(async () => {
  values.clear();
  root.dataset = { motion: "reduce", uiScale: "1.5" };
  for (const [key, value] of Object.entries({
    localStorage: { getItem: (key: string) => values.get(key) ?? null, setItem: (key: string, value: string) => values.set(key, value) },
    document: { documentElement: root }, window: new EventTarget(),
  })) {
    const descriptor = Object.getOwnPropertyDescriptor(globalThis, key);
    Object.defineProperty(globalThis, key, { configurable: true, value });
    restore.push(() => descriptor ? Object.defineProperty(globalThis, key, descriptor) : Reflect.deleteProperty(globalThis, key));
  }
  prefs = await import("../src/theme/appearancePrefs.ts");
});
afterEach(() => { restore.reverse().forEach(fn => fn()); restore = []; });

test("first start is Dark, contrast off and extra announcements off without altering motion/scale", () => {
  prefs.applyAppearancePrefs();
  assert.deepEqual(root.dataset, { motion: "reduce", uiScale: "1.5", theme: "dark", contrast: "normal", announcements: "off" });
  assert.equal(root.style.colorScheme, "dark");
  assert.equal(values.size, 0);
});

test("retired theme and contrast choices cannot override Horizon's standard appearance", () => {
  values.set("horizon.motion", "reduce"); values.set("horizon.uiScale", "1.5");
  values.set("horizon.theme", "light"); values.set("horizon.highContrast", "true");
  prefs.setAnnouncementsPref(true);
  prefs.applyAppearancePrefs();
  assert.equal(prefs.getAnnouncementsPref(), true);
  assert.equal(root.dataset.theme, "dark"); assert.equal(root.dataset.contrast, "normal");
  assert.equal(root.style.colorScheme, "dark");
  assert.equal(values.get("horizon.motion"), "reduce"); assert.equal(values.get("horizon.uiScale"), "1.5");
});

test("malformed stored values fall back safely and repeated selection does not emit updates", () => {
  values.set("horizon.theme", "sepia"); values.set("horizon.highContrast", "yes"); values.set("horizon.announcements", "1");
  let changes = 0;
  const unsubscribe = prefs.subscribeAppearancePrefs(() => changes++);
  prefs.applyAppearancePrefs();
  assert.equal(root.dataset.theme, "dark"); assert.equal(root.dataset.contrast, "normal");
  assert.equal(prefs.getAnnouncementsPref(), false);
  prefs.setAnnouncementsPref(true); prefs.setAnnouncementsPref(true);
  assert.equal(changes, 1);
  unsubscribe(); prefs.setAnnouncementsPref(false); assert.equal(changes, 1);
});

test("unavailable storage cannot prevent startup", () => {
  Object.defineProperty(globalThis, "localStorage", { configurable: true, get() { throw new Error("Storage blocked"); } });
  assert.doesNotThrow(() => prefs.applyAppearancePrefs());
  assert.equal(root.dataset.theme, "dark");
});

test("cross-tab announcements update while retired appearance keys stay inactive", () => {
  const stop = prefs.startAppearancePrefs();
  let updates = 0;
  const unsubscribe = prefs.subscribeAppearancePrefs(() => updates++);
  const storageEvent = (key: string | null) => {
    const event = new Event("storage"); Object.defineProperty(event, "key", { value: key });
    window.dispatchEvent(event);
  };
  values.set("horizon.theme", "light"); values.set("horizon.highContrast", "true");
  storageEvent("horizon.theme");
  assert.equal(root.dataset.theme, "dark"); assert.equal(root.dataset.contrast, "normal");
  assert.equal(updates, 0);
  values.set("horizon.announcements", "true"); storageEvent("horizon.announcements");
  assert.equal(root.dataset.announcements, "on");
  assert.equal(updates, 1);
  storageEvent("horizon.motion"); assert.equal(updates, 1);
  values.clear(); storageEvent(null);
  assert.equal(root.dataset.theme, "dark"); assert.equal(root.dataset.announcements, "off");
  assert.equal(root.dataset.motion, "reduce"); assert.equal(root.dataset.uiScale, "1.5");
  stop(); unsubscribe(); values.set("horizon.theme", "light"); storageEvent("horizon.theme");
  assert.equal(root.dataset.theme, "dark");
});
