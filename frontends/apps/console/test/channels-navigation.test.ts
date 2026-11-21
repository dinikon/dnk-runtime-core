import { test } from "node:test";
import assert from "node:assert/strict";
import { channelListReturnTo } from "../src/modules/channels/model/channel-navigation.ts";
import { channelRoutes } from "../src/modules/channels/routes.ts";

test("connection return restores only the internal list and its filters", () => {
  assert.equal(
    channelListReturnTo(
      "/channels?q=Shop&platform=prom&status=verified&offset=50#list",
    ),
    "/channels?q=Shop&platform=prom&status=verified&offset=50#list",
  );
  for (const value of [
    undefined,
    ["/channels"],
    "https://example.com/channels",
    "//example.com/channels",
    "/channels/other",
    "/channels-other",
    "/catalog/items",
    "/\\example.com/channels",
  ])
    assert.equal(channelListReturnTo(value), "/channels");
});

test("routes expose only connection list, creation and settings", () => {
  assert.deepEqual(
    channelRoutes.map((route) => route.name),
    ["channels", "channel-new", "channel-detail"],
  );
  assert.ok(channelRoutes.every((route) => route.component));
});
