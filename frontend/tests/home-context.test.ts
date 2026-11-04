import assert from "node:assert/strict";
import test from "node:test";
import { continueItems, focusFallback, parseMediaType, scopedPath } from "../src/home/context.ts";
import type { ContinueItem } from "../src/types.ts";

const item = (fileId: number, type: "movie" | "episode", position = 30, duration: number | null = 100, watched = false) =>
  ({ file_id: fileId, type, progress: { position, duration, watched } }) as ContinueItem;

test("only explicit movie/tv values establish a media context", () => {
  assert.equal(parseMediaType("movie"), "movie");
  assert.equal(parseMediaType("tv"), "tv");
  assert.equal(parseMediaType("all"), null);
  assert.equal(parseMediaType(null), null);
});

test("destination scope survives existing filters and hash fragments", () => {
  assert.equal(scopedPath("/discover?collection=4&sort=year#results", "movie"), "/discover?collection=4&sort=year&media=movie#results");
  assert.equal(scopedPath("/search?q=clip&media=movie", "tv"), "/search?q=clip&media=tv");
  assert.equal(scopedPath("/settings?section=libraries", null), "/settings?section=libraries");
});

test("movie and episode resume history never cross media type", () => {
  const rows = [item(1, "movie"), item(2, "episode"), item(3, "movie")];
  assert.deepEqual(continueItems(rows, "movie").map(row => row.file_id), [1, 3]);
  assert.deepEqual(continueItems(rows, "tv").map(row => row.file_id), [2]);
});

test("only actual finite unfinished progress is offered for resume", () => {
  const rows = [item(1, "movie", 1), item(2, "movie", 0), item(3, "movie", 100), item(4, "movie", 10, null),
    item(5, "movie", 30, 100, true), item(6, "movie", NaN), item(7, "movie", 20, Infinity), item(8, "movie", -1), item(9, "movie", 20, 0)];
  assert.deepEqual(continueItems(rows, "movie").map(row => row.file_id), [1]);
  assert.deepEqual(continueItems([], "tv"), []);
});

test("restoration retains a surviving item then chooses the nearest valid replacement", () => {
  assert.equal(focusFallback("resume-2", 1, ["resume-1", "resume-2"], "hub-atlas"), "resume-2");
  assert.equal(focusFallback("resume-2", 1, ["resume-1", "resume-3"], "hub-atlas"), "resume-3");
  assert.equal(focusFallback("resume-3", 2, ["resume-1"], "hub-atlas"), "resume-1");
  assert.equal(focusFallback("resume-1", 0, [], "hub-search"), "hub-search");
});
