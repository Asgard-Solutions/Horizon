import { readFileSync } from "node:fs";
import postcss from "postcss";
import { transform } from "lightningcss";

// Small CSS fixture evaluator: parses real selectors, applies specificity/order, resolves inherited tokens.
// This checks shipped declarations without a browser, including :is(), pseudo-elements and input states.
type Part = any;
export type ElementFixture = {
  tag: string; classes?: string[]; attrs?: Record<string, string>; states?: string[];
  pseudo?: string; parent?: ElementFixture;
};
const files = ["theme/horizon.theme.css", "styles.css", "home/home.css", "detail/detail.css", "player/player.css", "discover/discover.css", "settings/settings.css", "home/hub.css", "theme/appearance.css"];
const rules: { selectors: Part[][]; declarations: { prop: string; value: string; important: boolean }[]; correction: boolean }[] = [];
for (const file of files) {
  const css = postcss.parse(readFileSync(new URL(`../src/${file}`, import.meta.url), "utf8"));
  css.walkRules(rule => {
    let parent: any = rule.parent;
    let correction = false;
    while (parent?.type !== "root") {
      if (parent?.type !== "atrule" || parent.name !== "media" || parent.params !== "(forced-colors: none)") return;
      correction = true; parent = parent.parent;
    }
    let selectors: Part[][] = [];
    transform({ filename: "fixture.css", code: Buffer.from(`${rule.selector}{color:inherit}`), visitor: {
      Rule(parsed: any) { if (parsed.type === "style") selectors = parsed.value.selectors; },
    } });
    const declarations: { prop: string; value: string; important: boolean }[] = [];
    rule.walkDecls(decl => declarations.push({ prop: decl.prop, value: decl.value, important: !!decl.important }));
    rules.push({ selectors, declarations, correction });
  });
}
function specificity(parts: Part[]): number {
  return parts.reduce((sum, part) => sum + (part.type === "id" ? 10000 : part.type === "type" || part.type === "pseudo-element" ? 1
    : part.type === "class" || part.type === "attribute" ? 100 : part.type === "pseudo-class"
      ? part.kind === "where" ? 0 : part.selectors ? Math.max(...part.selectors.map(specificity)) : 100 : 0), 0);
}
function matches(parts: Part[], element: ElementFixture): boolean {
  const index = parts.findLastIndex(part => part.type === "combinator");
  if (index >= 0) {
    if (!matches(parts.slice(index + 1), element)) return false;
    for (let ancestor = element.parent; ancestor; ancestor = ancestor.parent) {
      if (matches(parts.slice(0, index), ancestor)) return true;
      if (parts[index].value !== "descendant") break;
    }
    return false;
  }
  if (!!element.pseudo !== parts.some(part => part.type === "pseudo-element")) return false;
  return parts.every(part => {
    if (part.type === "universal") return true;
    if (part.type === "type") return element.tag === part.name;
    if (part.type === "class") return element.classes?.includes(part.name);
    if (part.type === "attribute") return part.operation?.operator === "equal" ? element.attrs?.[part.name] === part.operation.value : part.name in (element.attrs ?? {});
    if (part.type === "pseudo-element") return element.pseudo === part.kind;
    if (part.type === "pseudo-class") {
      if (part.kind === "root") return !element.parent;
      if (part.kind === "is" || part.kind === "where") return part.selectors.some((selector: Part[]) => matches(selector, element));
      if (part.kind === "not") return !part.selectors.some((selector: Part[]) => matches(selector, element));
      return element.states?.includes(part.kind);
    }
    return false;
  });
}
export function cssStyle(element: ElementFixture, includeCorrection = true): Record<string, string> {
  const inherited = element.parent ? cssStyle(element.parent, includeCorrection) : {};
  const values: Record<string, string> = Object.fromEntries(Object.entries(inherited).filter(([key]) => key.startsWith("--")));
  const priorities: Record<string, number> = {};
  for (const rule of rules) {
    if (!includeCorrection && rule.correction) continue;
    const selected = rule.selectors.filter(selector => matches(selector, element));
    if (!selected.length) continue;
    const weight = Math.max(...selected.map(specificity));
    for (const decl of rule.declarations) {
      const priority = weight + (decl.important ? 1000000 : 0);
      if (priority < (priorities[decl.prop] ?? -1)) continue;
      priorities[decl.prop] = priority; values[decl.prop] = decl.value;
    }
  }
  const resolve = (value: string, depth = 0): string => depth > 20 ? value : value.replace(/var\((--[\w-]+)(?:,\s*([^()]*))?\)/g,
    (_, key, fallback) => resolve(values[key] ?? fallback ?? `unresolved(${key})`, depth + 1));
  return Object.fromEntries(Object.entries(values).map(([key, value]) => [key, resolve(value)]));
}
export function screen(theme: string, high: boolean, input = "keys") {
  const root: ElementFixture = { tag: "html", attrs: { "data-theme": theme, "data-contrast": high ? "high" : "normal" } };
  return { tag: "body", attrs: { "data-input": input }, parent: root } as ElementFixture;
}
export const child = (parent: ElementFixture, classes: string[], tag = "div", states: string[] = []): ElementFixture => ({ tag, classes, states, parent });
