import assert from "node:assert/strict";
import { test } from "node:test";
import { createAnnouncer, routeAnnouncement } from "../src/accessibility/announcements.ts";

test("announcements require opt-in, coalesce navigation and suppress duplicate route requests", (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const output: string[] = [];
  const region = createAnnouncer(text => output.push(text));
  region.announce("Home", "route:/"); t.mock.timers.tick(200);
  assert.deepEqual(output, []);
  region.setEnabled(true);
  region.announce("Home", "route:/"); region.announce("Discover", "route:/discover");
  t.mock.timers.tick(200);
  assert.equal(output.at(-1), "Discover");
  const length = output.length;
  region.announce("Discover", "route:/discover"); t.mock.timers.tick(200);
  assert.equal(output.length, length);
  region.dispose();
});

test("turning off cancels queued messages and repeated explicit tests still announce", (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  let text = "";
  const region = createAnnouncer(value => { text = value; });
  region.setEnabled(true);
  region.announce("Test announcement"); t.mock.timers.tick(200); assert.equal(text, "Test announcement");
  region.announce("Test announcement"); assert.equal(text, "");
  t.mock.timers.tick(200); assert.equal(text, "Test announcement");
  region.announce("Pending"); region.setEnabled(false); t.mock.timers.tick(200); assert.equal(text, "");
  region.setEnabled(true); t.mock.timers.tick(200); assert.equal(text, "");
  region.announce("Unmounted"); region.dispose(); t.mock.timers.tick(200); assert.equal(text, "");
});

test("route context covers actual pages without announcing query typing, focus-selected settings or polling", () => {
  const paths = [["/", "REELHEIM Home"], ["/home/movie", "Movies Home"], ["/home/tv", "TV Shows Home"],
    ["/discover", "Discover"], ["/atlas", "Library Atlas"], ["/search", "Search"],
    ["/movies/12", "Movie details"], ["/shows/8", "TV show details"], ["/play/4", "Media player"], ["/settings", "Settings"]];
  for (const [path, label] of paths) assert.equal(routeAnnouncement(path, "").message, `${label} page.`);
  assert.deepEqual(routeAnnouncement("/settings", "?section=display"), routeAnnouncement("/settings", "?section=accessibility"));
  assert.deepEqual(routeAnnouncement("/search", "?q=a"), routeAnnouncement("/search", "?q=alien"));
  assert.equal(routeAnnouncement("/discover", "?media=tv").message, "TV Shows: Discover page.");
  assert.notEqual(routeAnnouncement("/movies/12", "").key, routeAnnouncement("/movies/13", "").key);
});
