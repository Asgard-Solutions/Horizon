import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { registerHooks } from "node:module";
import { test } from "node:test";
import ts from "typescript";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

// Compile the real TSX in memory with the project's existing TypeScript. No app/server/browser needed.
registerHooks({
  resolve(specifier, context, next) {
    if (specifier.startsWith(".") && context.parentURL?.startsWith("file:")) {
      for (const suffix of ["", ".ts", ".tsx"]) {
        const url = new URL(specifier + suffix, context.parentURL);
        if (existsSync(url) && /\.(tsx?|png)$/.test(url.pathname)) return { url: url.href, shortCircuit: true };
      }
    }
    return next(specifier, context);
  },
  load(url, context, next) {
    if (url.endsWith(".png")) return { format: "module", source: `export default ${JSON.stringify(url)}`, shortCircuit: true };
    if (/\.tsx?$/.test(url) && url.includes("/src/")) return {
      format: "module", shortCircuit: true,
      source: ts.transpileModule(readFileSync(new URL(url), "utf8"), {
        compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
      }).outputText,
    };
    return next(url, context);
  },
});

test("announcement output is a single initially empty polite atomic status region", async () => {
  const { AnnouncementProvider } = await import("../src/accessibility/Announcer.tsx");
  const html = renderToStaticMarkup(createElement(AnnouncementProvider, { children: createElement("button", null, "Keep focus") }));
  assert.match(html, /role="status" aria-live="polite" aria-atomic="true"/);
  assert.match(html, /data-testid="screen-reader-announcements"><\/div>/);
  assert.equal((html.match(/aria-live=/g) ?? []).length, 1);
  assert.ok(html.includes("Keep focus"));
});

test("screen reader controls remain available without the retired High contrast switch", async () => {
  const old = Object.getOwnPropertyDescriptor(globalThis, "window");
  const oldStorage = Object.getOwnPropertyDescriptor(globalThis, "localStorage");
  Object.defineProperty(globalThis, "window", { configurable: true, value: { matchMedia: () => ({ matches: false }) } });
  Object.defineProperty(globalThis, "localStorage", { configurable: true, value: { getItem: () => null } });
  try {
    const { AccessibilitySection } = await import("../src/settings/AccessibilitySection.tsx");
    const html = renderToStaticMarkup(createElement(AccessibilitySection));
    assert.doesNotMatch(html, /High contrast|a11y-contrast/);
    assert.match(html, /role="switch" aria-label="Additional screen reader announcements" aria-checked="false"/);
    assert.match(html, /<button[^>]*disabled=""[^>]*data-testid="a11y-reader-test"/);
    assert.ok(html.includes("ARIA live regions"));
    assert.ok(!html.includes("Coming later"));
  } finally {
    if (old) Object.defineProperty(globalThis, "window", old); else Reflect.deleteProperty(globalThis, "window");
    if (oldStorage) Object.defineProperty(globalThis, "localStorage", oldStorage); else Reflect.deleteProperty(globalThis, "localStorage");
  }
});

test("only standard branding, scaling and announcements remain despite retired saved choices", async () => {
  const saved = new Map([["horizon.theme", "light"], ["horizon.highContrast", "true"], ["horizon.announcements", "true"]]);
  const restore: (() => void)[] = [];
  const screen = Object.assign(new EventTarget(), { innerWidth: 1920, innerHeight: 1080, devicePixelRatio: 1, matchMedia: () => ({ matches: false }) });
  const root = { dataset: {}, style: { colorScheme: "", zoom: "", setProperty() {} } };
  for (const [name, value] of Object.entries({ window: screen, document: { documentElement: root }, CSS: { supports: () => true },
    localStorage: { getItem: (key: string) => saved.get(key) ?? null, setItem: (key: string, value: string) => saved.set(key, value) } })) {
    const descriptor = Object.getOwnPropertyDescriptor(globalThis, name);
    Object.defineProperty(globalThis, name, { configurable: true, value });
    restore.push(() => descriptor ? Object.defineProperty(globalThis, name, descriptor) : Reflect.deleteProperty(globalThis, name));
  }
  try {
    const { MemoryRouter } = await import("react-router-dom");
    const { PrimaryNav } = await import("../src/components/PrimaryNav.tsx");
    const { DisplaySection } = await import("../src/settings/DisplaySection.tsx");
    const { AccessibilitySection } = await import("../src/settings/AccessibilitySection.tsx");
    for (const [width, height] of [[1920, 1080], [390, 844]]) {
      screen.innerWidth = width; screen.innerHeight = height;
      const nav = renderToStaticMarkup(createElement(MemoryRouter, { children: createElement(PrimaryNav) }));
      assert.match(nav, /reelheim-logo-header-1120\.png/);
      assert.doesNotMatch(nav, /horizon-media-center-logo-on-light\.png/);
      const display = renderToStaticMarkup(createElement(DisplaySection));
      assert.doesNotMatch(display, /display-theme|High contrast|Dark|Light/);
      assert.match(display, /Interface size/);
      const a11y = renderToStaticMarkup(createElement(AccessibilitySection));
      assert.doesNotMatch(a11y, /High contrast|a11y-contrast/);
      assert.match(a11y, /aria-label="Additional screen reader announcements" aria-checked="true"/);
      assert.match(a11y, /<button type="button" class="hbtn" data-testid="a11y-reader-test"/);
    }
    saved.set("horizon.theme", "dark");
    const dark = renderToStaticMarkup(createElement(MemoryRouter, { children: createElement(PrimaryNav) }));
    assert.match(dark, /reelheim-logo-header-1120\.png/);
  } finally { restore.reverse().forEach(fn => fn()); }
});

test("synchronous startup applies appearance alongside existing motion and manual scaling", async () => {
  const restore: (() => void)[] = [];
  const values = new Map([["horizon.theme", "light"], ["horizon.highContrast", "true"], ["horizon.motion", "reduce"], ["horizon.uiScale", "1.5"]]);
  const root = { dataset: {} as Record<string, string>, style: { colorScheme: "", zoom: "", setProperty() {} } };
  for (const [name, value] of Object.entries({ document: { documentElement: root }, CSS: { supports: () => true },
    window: Object.assign(new EventTarget(), { innerWidth: 3840, innerHeight: 2160 }),
    localStorage: { getItem: (key: string) => values.get(key) ?? null } })) {
    const descriptor = Object.getOwnPropertyDescriptor(globalThis, name);
    Object.defineProperty(globalThis, name, { configurable: true, value });
    restore.push(() => descriptor ? Object.defineProperty(globalThis, name, descriptor) : Reflect.deleteProperty(globalThis, name));
  }
  try {
    const { startDisplayPrefs } = await import("../src/theme/displayPrefs.ts");
    startDisplayPrefs();
    assert.deepEqual(root.dataset, { theme: "dark", contrast: "normal", announcements: "off", motion: "reduce", uiScale: "1.5" });
    assert.equal(root.style.zoom, "1.5"); assert.equal(root.style.colorScheme, "dark");
  } finally { restore.reverse().forEach(fn => fn()); }
});
