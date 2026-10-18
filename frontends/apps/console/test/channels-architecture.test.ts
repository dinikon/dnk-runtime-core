import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
const root = new URL("../src/modules/channels/", import.meta.url);
test("presentational Channels UI has no HTTP, router, cache or session dependencies", () => {
  for (const file of readdirSync(new URL("ui/", root)).filter((name) =>
    name.endsWith(".vue"),
  )) {
    const source = readFileSync(new URL(`ui/${file}`, root), "utf8");
    assert.doesNotMatch(
      source,
      /from\s+["'][^"']*(?:\/api\/|\/queries\/|\/mutations\/|\/app\/stores|vue-router|vue-query)/,
      file,
    );
  }
});
test("Channels models and API retain the declared direction of dependencies", () => {
  for (const file of [
    "model/channels.types.ts",
    "model/channels.query-keys.ts",
    "model/channels.presentation.ts",
  ]) {
    assert.doesNotMatch(
      readFileSync(new URL(file, root), "utf8"),
      /from\s+["'][^"']*(?:\/api\/|\/pages\/|\/ui\/|vue-router|\/app\/stores)/,
      file,
    );
  }
  for (const file of [
    "api/channels.dto.ts",
    "api/channels.mapper.ts",
    "api/channels.api.ts",
  ]) {
    assert.doesNotMatch(
      readFileSync(new URL(file, root), "utf8"),
      /from\s+["'][^"']*(?:\/pages\/|\/ui\/|vue-router|vue-query|\/app\/stores)/,
      file,
    );
  }
});
