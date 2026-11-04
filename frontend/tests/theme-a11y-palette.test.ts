import assert from "node:assert/strict";
import { test } from "node:test";
import { child, cssStyle, screen } from "./theme-a11y-css.ts";
test("standard Home keyboard and mouse focus retain the approved artwork styling", () => {
  for (const [theme, input] of [["dark", "keys"], ["dark", "mouse"]]) {
    const home = child(screen(theme, false, input), ["home-shell", "home-shell--selection"]);
    const card = child(child(home, ["hub-choices--types"]), ["hub-card"], "a", ["focus"]);
    assert.deepEqual(cssStyle(card), cssStyle(card, false));
  }
});

test("media cards use the same gold glow for hover and keyboard/gamepad focus, with neutral mouse restoration", () => {
  const card = (input: string, states: string[]) => {
    const home = child(screen("dark", false, input), ["home-shell", "home-shell--selection"]);
    return cssStyle(child(child(home, ["hub-choices--types"]), ["hub-card"], "a", states));
  };
  const neutral = card("mouse", ["focus"])["box-shadow"];
  const keyboard = card("keys", ["focus"])["box-shadow"];
  assert.match(keyboard, /#ffce69/i);
  assert.notEqual(keyboard, neutral);
  assert.equal(card("mouse", ["hover"])["box-shadow"], keyboard);
  assert.equal(card("mouse", ["focus", "hover"])["box-shadow"], keyboard);
  assert.equal(card("pad", ["focus"])["box-shadow"], keyboard);
});
