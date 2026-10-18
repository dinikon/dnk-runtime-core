import { test } from "node:test";
import assert from "node:assert/strict";
import {
  ProductAutosave,
  type AutosaveState,
} from "../src/modules/catalog/model/product-autosave.ts";

const state = (): AutosaveState => ({
  entries: {},
  pending: false,
  paused: false,
  error: "",
  held: false,
});
const tick = (ms = 25) => new Promise((resolve) => setTimeout(resolve, ms));

test("debounce combines sections and sends the latest value", async () => {
  const current = state(),
    requests: unknown[] = [];
  const queue = new ProductAutosave(
    current,
    async (value) => {
      requests.push(value);
    },
    async () => {},
    () => ({ fields: {}, message: "error" }),
    10,
  );
  queue.stage("sku", { sku: "a" });
  queue.stage("status", { status: "active" });
  queue.stage("sku", { sku: "b" });
  assert.equal(requests.length, 0);
  await tick();
  assert.deepEqual(requests, [{ sku: "b", status: "active" }]);
  assert.deepEqual(current.entries, {});
  queue.cancel();
});

test("editing during a slow request stays dirty and is sent in order", async () => {
  const current = state(),
    requests: unknown[] = [];
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  const queue = new ProductAutosave(
    current,
    async (value) => {
      requests.push(value);
      if (requests.length === 1) await gate;
    },
    async () => {},
    () => ({ fields: {}, message: "error" }),
    10,
  );
  queue.stage("sku", { sku: "first" });
  const flushing = queue.flush();
  await tick(1);
  queue.stage("sku", { sku: "second" });
  assert.equal(current.entries.sku?.value.sku, "second");
  release();
  await flushing;
  assert.deepEqual(requests, [{ sku: "first" }, { sku: "second" }]);
  assert.deepEqual(current.entries, {});
  queue.cancel();
});

test("invalid sections stay in the draft while valid sections save", async () => {
  const current = state(),
    requests: unknown[] = [];
  const queue = new ProductAutosave(
    current,
    async (value) => {
      requests.push(value);
    },
    async () => {},
    () => ({ fields: {}, message: "error" }),
  );
  queue.stage(
    "content",
    { content: { expected_schema_version: 1, values: { title: "" } } },
    "Name required",
  );
  queue.stage("sku", { sku: "valid" });
  await queue.flush();
  assert.deepEqual(requests, [{ sku: "valid" }]);
  assert.equal(current.entries.content?.error, "Name required");
  queue.cancel();
});

test("server field failure rolls back the batch and retries the other sections", async () => {
  const current = state(),
    requests: unknown[] = [];
  const queue = new ProductAutosave(
    current,
    async (value) => {
      requests.push(value);
      if (requests.length === 1) throw new Error("duplicate sku");
    },
    async () => {},
    () => ({ fields: { sku: "Already used" }, message: "error" }),
  );
  queue.stage("sku", { sku: "duplicate" });
  queue.stage("virtual", { virtual: true });
  await queue.flush();
  assert.deepEqual(requests, [
    { sku: "duplicate", virtual: true },
    { virtual: true },
  ]);
  assert.equal(current.entries.sku?.error, "Already used");
  assert.equal(current.paused, false);
  queue.cancel();
});

test("network failure pauses until retry and preserves the latest draft", async () => {
  const current = state();
  let attempts = 0;
  const queue = new ProductAutosave(
    current,
    async () => {
      if (++attempts === 1) throw new Error("offline");
    },
    async () => {},
    () => ({ fields: {}, message: "offline" }),
    10,
  );
  queue.stage("sku", { sku: "kept" });
  await queue.flush();
  assert.equal(current.paused, true);
  queue.stage("sku", { sku: "latest" });
  await tick();
  assert.equal(attempts, 1);
  queue.retry();
  await tick();
  assert.equal(attempts, 2);
  assert.deepEqual(current.entries, {});
  queue.cancel();
});

test("context cancellation ignores late success and clears scheduled writes", async () => {
  const current = state();
  let release!: () => void,
    acknowledgements = 0;
  const queue = new ProductAutosave(
    current,
    async () =>
      new Promise<void>((resolve) => {
        release = resolve;
      }),
    async () => {
      acknowledgements++;
    },
    () => ({ fields: {}, message: "error" }),
  );
  queue.stage("sku", { sku: "old tenant" });
  const flushing = queue.flush();
  queue.cancel();
  release();
  await flushing;
  assert.equal(acknowledgements, 0);
  assert.deepEqual(current.entries, {});
});

test("a late old-context response cannot acknowledge the new context's draft", async () => {
  const current = state(),
    requests: unknown[] = [];
  let release!: () => void;
  const queue = new ProductAutosave(
    current,
    async (value) => {
      requests.push(value);
      if (requests.length === 1)
        await new Promise<void>((resolve) => {
          release = resolve;
        });
    },
    async () => {},
    () => ({ fields: {}, message: "error" }),
    10,
  );
  queue.stage("sku", { sku: "old" });
  const first = queue.flush();
  queue.cancel();
  queue.stage("sku", { sku: "new" });
  release();
  await first;
  await tick();
  assert.deepEqual(requests, [{ sku: "old" }, { sku: "new" }]);
  assert.deepEqual(current.entries, {});
  queue.cancel();
});
