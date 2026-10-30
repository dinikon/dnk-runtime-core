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

test("old publication-list links retain their context on the connection page", () => {
  const route = channelRoutes.find(
    (route) => route.name === "channel-publications",
  );
  assert.equal(typeof route?.redirect, "function");
  if (typeof route?.redirect !== "function") return;
  const query = {
    q: "SKU-1",
    offset: "50",
    limit: "25",
    locale: "uk",
    binding_filter: "unlinked",
    returnTo: "/channels?platform=prom",
  };
  const result = route.redirect({
    params: { id: "shop / 1" },
    query,
    hash: "#row",
  } as Parameters<typeof route.redirect>[0]);
  assert.deepEqual(result, {
    name: "channel-detail",
    params: { id: "shop / 1" },
    query,
    hash: "#row",
  });
  assert.ok(
    channelRoutes.find((route) => route.name === "channel-publication")
      ?.component,
  );
});
