import { test } from "node:test";
import assert from "node:assert/strict";
import {
  feedFilters,
  feedListReturnTo,
  lastFeedOffset,
} from "../src/modules/feed-builder/model/feed.navigation.ts";
import { feedKeys } from "../src/modules/feed-builder/model/feed.query-keys.ts";
import { FeedRequestGuard } from "../src/modules/feed-builder/model/feed.request-guard.ts";
test("URL restores server filters and bounded pagination; default excludes archives", () => {
  assert.deepEqual(
    feedFilters({ q: "prom", status: "ARCHIVED", offset: "101" }),
    { search: "prom", status: "ARCHIVED", limit: 50, offset: 100 },
  );
  for (const offset of ["-1", "oops", "Infinity", "9007199254740992", ["50"]])
    assert.equal(feedFilters({ offset }).offset, 0);
  assert.equal(feedFilters({ status: "ONLY_SINGLE" }).status, "");
  assert.equal(feedFilters({ q: "a".repeat(300) }).search.length, 255);
  assert.equal(lastFeedOffset(50, 50), 0);
  assert.equal(lastFeedOffset(51, 50), 50);
  assert.equal(lastFeedOffset(0, 50), 0);
});
test("Return navigation retains list filters but never accepts external or unrelated routes", () => {
  assert.equal(
    feedListReturnTo("/feed-builder/feeds?status=ARCHIVED&offset=50#rows"),
    "/feed-builder/feeds?status=ARCHIVED&offset=50#rows",
  );
  for (const path of [
    "//evil.example/feed-builder/feeds",
    "https://evil.example",
    "javascript:alert(1)",
    "/channels",
    "http://[",
    ["/feed-builder/feeds"],
  ])
    assert.equal(feedListReturnTo(path), "/feed-builder/feeds");
});
test("Query keys isolate tenant, user, session, filters and detail identity", () => {
  const scope = ["tenant-a", "user-a", "1"] as const,
    filters = feedFilters({});
  const first = feedKeys.list(scope, filters);
  assert.notDeepEqual(
    first,
    feedKeys.list(["tenant-b", "user-a", "1"], filters),
  );
  assert.notDeepEqual(
    first,
    feedKeys.list(["tenant-a", "user-b", "1"], filters),
  );
  assert.notDeepEqual(
    first,
    feedKeys.list(["tenant-a", "user-a", "2"], filters),
  );
  assert.notDeepEqual(
    first,
    feedKeys.list(scope, { ...filters, status: "ARCHIVED" }),
  );
  assert.notDeepEqual(
    feedKeys.detail(scope, "one"),
    feedKeys.detail(scope, "two"),
  );
});
test("Pending blocks duplicate submit; cancelling a scope rejects late completion even after returning to that identity", async () => {
  const guard = new FeedRequestGuard(),
    original = guard.start()!;
  assert.equal(guard.start(), undefined);
  let resolve!: (value: string) => void;
  const deferred = new Promise<string>((done) => {
    resolve = done;
  });
  let applied = "";
  const task = deferred.then((value) => {
    if (guard.current(original)) applied = value;
  });
  guard.cancel();
  assert.equal(original.signal.aborted, true);
  const current = guard.start()!;
  resolve("late tenant A response");
  await task;
  assert.equal(applied, "");
  guard.finish(original);
  assert.equal(guard.current(current), true);
  guard.finish(current);
  assert.ok(guard.start());
  guard.dispose();
  assert.equal(guard.start(), undefined);
});
