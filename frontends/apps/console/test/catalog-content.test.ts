import { test } from "node:test";
import assert from "node:assert/strict";
import { changeProductContent } from "../src/modules/catalog/model/product-content-draft.ts";
import {
  ProductAutosave,
  type AutosaveState,
} from "../src/modules/catalog/model/product-autosave.ts";

test("separate editors preserve name, both descriptions and optional block semantics", () => {
  const source = { name: "Original", short_desc: "Short", desc: "Full" };
  let values = changeProductContent(source, "name", "Changed");
  values = changeProductContent(values, "short_desc", "");
  values = changeProductContent(values, "desc", undefined);
  assert.deepEqual(values, { name: "Changed", short_desc: "" });
  assert.deepEqual(source, {
    name: "Original",
    short_desc: "Short",
    desc: "Full",
  });
});

test("typing in multiple content editors during a slow PATCH preserves the newest complete snapshot", async () => {
  const state: AutosaveState = {
    entries: {},
    pending: false,
    paused: false,
    held: false,
    error: "",
  };
  const sent: unknown[] = [];
  let release!: () => void;
  const queue = new ProductAutosave(
    state,
    async (patch) => {
      sent.push(patch);
      if (sent.length === 1)
        await new Promise<void>((resolve) => {
          release = resolve;
        });
    },
    async () => {},
    () => ({ fields: {}, message: "error" }),
  );
  let values: Record<string, string> = { name: "Original", desc: "Full" };
  values = changeProductContent(values, "name", "New name");
  queue.stage("content", { content: { expected_schema_version: 1, values } });
  const flush = queue.flush();
  values = changeProductContent(values, "short_desc", "New short");
  values = changeProductContent(values, "desc", "New full");
  queue.stage("content", { content: { expected_schema_version: 1, values } });
  release();
  await flush;
  assert.deepEqual(sent, [
    {
      content: {
        expected_schema_version: 1,
        values: { name: "New name", desc: "Full" },
      },
    },
    {
      content: {
        expected_schema_version: 1,
        values: { name: "New name", short_desc: "New short", desc: "New full" },
      },
    },
  ]);
  assert.deepEqual(state.entries, {});
  queue.cancel();
});
