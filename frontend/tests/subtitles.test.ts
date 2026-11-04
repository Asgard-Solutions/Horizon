import assert from "node:assert/strict";
import test from "node:test";
import { automaticSubtitle, observeSubtitleLoad, positionSubtitleCues, setSubtitleModes } from "../src/player/subtitles.ts";

const tracks = [{ id: "fr", language: "fr" }, { id: "en", language: "en" }, { id: "plain", language: null }];

test("subtitles clear the custom controls then return to the bottom when controls hide", () => {
  const cues = [{ line: -1, snapToLines: true, lineAlign: "start" }, { line: -1, snapToLines: true, lineAlign: "start" }];
  positionSubtitleCues(cues, true);
  assert.deepEqual(cues, [{ line: 60, snapToLines: false, lineAlign: "end" }, { line: 60, snapToLines: false, lineAlign: "end" }]);
  positionSubtitleCues(cues, false);
  assert.deepEqual(cues, [{ line: 85, snapToLines: false, lineAlign: "end" }, { line: 85, snapToLines: false, lineAlign: "end" }]);
});

test("Off never automatically selects a subtitle, including an empty library", () => {
  assert.equal(automaticSubtitle(tracks, "off", ["en-US"]), null);
  assert.equal(automaticSubtitle([], "auto", ["en-US"]), null);
});

test("native track load/error is observed once and cached loads cannot miss their ready signal", () => {
  const track = Object.assign(new EventTarget(), { readyState: 0 });
  const results: boolean[] = [];
  const stop = observeSubtitleLoad(track, failed => results.push(failed));
  track.dispatchEvent(new Event("load"));
  track.dispatchEvent(new Event("error"));
  assert.deepEqual(results, [false]);
  stop();
  track.readyState = 2;
  observeSubtitleLoad(track, failed => results.push(failed))();
  assert.deepEqual(results, [false, false]);
  track.readyState = 3;
  observeSubtitleLoad(track, failed => results.push(failed))();
  assert.deepEqual(results, [false, false, true]);
});

test("leaving a subtitle removes its native listeners before late events arrive", () => {
  const track = Object.assign(new EventTarget(), { readyState: 0 });
  let count = 0;
  observeSubtitleLoad(track, () => count++)();
  track.dispatchEvent(new Event("load"));
  assert.equal(count, 0);
});

test("automatic subtitles respect language priority, region and untagged fallback", () => {
  assert.equal(automaticSubtitle(tracks, "auto", ["de-DE", "en-US"]), "en");
  assert.equal(automaticSubtitle(tracks, "auto", ["de"]), "plain");
  assert.equal(automaticSubtitle(tracks.slice(0, 2), "auto", []), "fr");
  assert.equal(automaticSubtitle([{ id: "gb", language: "en-GB" }, { id: "us", language: "en-US" }], "auto", ["en-US"]), "us");
});

test("selection enables one subtitle and Off disables every subtitle without touching metadata", () => {
  const modes = [{ id: "fr", kind: "subtitles", mode: "disabled" }, { id: "en", kind: "subtitles", mode: "showing" },
    { id: "chapters", kind: "metadata", mode: "hidden" }];
  setSubtitleModes(modes, "fr");
  assert.deepEqual(modes.map(t => t.mode), ["showing", "disabled", "hidden"]);
  setSubtitleModes(modes, null);
  assert.deepEqual(modes.map(t => t.mode), ["disabled", "disabled", "hidden"]);
  setSubtitleModes(modes, "removed");
  assert.deepEqual(modes.map(t => t.mode), ["disabled", "disabled", "hidden"]);
});
