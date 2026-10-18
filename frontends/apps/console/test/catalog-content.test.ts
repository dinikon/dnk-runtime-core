import { test } from "node:test";
import assert from "node:assert/strict";
import { changeProductContent } from "../src/modules/catalog/model/product-content-draft.ts";
import {
  ProductAutosave,
  type AutosaveState,
} from "../src/modules/catalog/model/product-autosave.ts";

test("title and body editors preserve optional body semantics", () => {
  const source = { title: "Original", body: "Full" };
  let values = changeProductContent(source, "title", "Changed");
  values = changeProductContent(values, "body", "");
  assert.deepEqual(values, { title: "Changed", body: "" });
  values = changeProductContent(values, "body", undefined);
  assert.deepEqual(values, { title: "Changed" });
  assert.deepEqual(source, { title: "Original", body: "Full" });
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
  let values: Record<string, string> = { title: "Original", body: "Full" };
  values = changeProductContent(values, "title", "New name");
  queue.stage("content", { content: { expected_schema_version: 1, values } });
  const flush = queue.flush();
  values = changeProductContent(values, "body", "New full");
  queue.stage("content", { content: { expected_schema_version: 1, values } });
  release();
  await flush;
  assert.deepEqual(sent, [
    {
      content: {
        expected_schema_version: 1,
        values: { title: "New name", body: "Full" },
      },
    },
    {
      content: {
        expected_schema_version: 1,
        values: { title: "New name", body: "New full" },
      },
    },
  ]);
  assert.deepEqual(state.entries, {});
  queue.cancel();
});
