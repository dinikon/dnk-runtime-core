import { test } from "node:test";
import assert from "node:assert/strict";
import {
  ProductCreation,
  productCreationState,
} from "../src/modules/catalog/model/product-creation.ts";

test("choice is explicit and both presets only change virtual", async () => {
  const sent: boolean[] = [],
    opened: string[] = [];
  const state = productCreationState();
  const creation = new ProductCreation(
    state,
    async (virtual) => {
      sent.push(virtual);
      return { id: String(sent.length) };
    },
    async (id) => {
      opened.push(id);
    },
    () => ({ message: "error", uncertain: false }),
  );
  assert.deepEqual(sent, []);
  await creation.create("simple");
  creation.cancel();
  await creation.create("service");
  assert.deepEqual(sent, [false, true]);
  assert.deepEqual(opened, ["1", "2"]);
});

test("double activation while POST is pending creates one item", async () => {
  let release!: (value: { id: string }) => void;
  let requests = 0;
  const state = productCreationState();
  const creation = new ProductCreation(
    state,
    () => {
      requests++;
      return new Promise((resolve) => {
        release = resolve;
      });
    },
    async () => {},
    () => ({ message: "error", uncertain: false }),
  );
  const first = creation.create("simple");
  await creation.create("service");
  assert.equal(requests, 1);
  assert.equal(state.preset, "simple");
  release({ id: "one" });
  await first;
  assert.equal(state.pending, false);
});

test("navigation or cache failure after successful creation never repeats POST", async () => {
  let requests = 0,
    opens = 0;
  const state = productCreationState();
  const creation = new ProductCreation(
    state,
    async () => {
      requests++;
      return { id: "created" };
    },
    async (id) => {
      assert.equal(id, "created");
      if (++opens === 1) throw new Error("navigation");
    },
    () => ({ message: "error", uncertain: true }),
  );
  await creation.create("service");
  assert.equal(state.createdId, "created");
  assert.equal(state.uncertain, false);
  assert.match(state.error, /Товар создан/);
  await creation.create("service");
  assert.equal(requests, 1);
  assert.equal(opens, 2);
  assert.equal(state.error, "");
});

test("unknown POST outcome blocks retry; confirmed rejection allows explicit retry", async () => {
  for (const uncertain of [true, false]) {
    let requests = 0;
    const state = productCreationState();
    const creation = new ProductCreation(
      state,
      async () => {
        requests++;
        throw new Error("failed");
      },
      async () => {},
      () => ({ message: "failed", uncertain }),
    );
    await creation.create("simple");
    await creation.create("simple");
    assert.equal(requests, uncertain ? 1 : 2);
    assert.equal(state.createdId, null);
    assert.equal(state.pending, false);
  }
});

test("late old-session result cannot navigate or finish the new session's request", async () => {
  const releases: ((value: { id: string }) => void)[] = [],
    opened: string[] = [];
  const state = productCreationState();
  const creation = new ProductCreation(
    state,
    () =>
      new Promise((resolve) => {
        releases.push(resolve);
      }),
    async (id) => {
      opened.push(id);
    },
    () => ({ message: "error", uncertain: false }),
  );
  const old = creation.create("simple");
  creation.cancel();
  const current = creation.create("service");
  releases[0]!({ id: "old" });
  await old;
  assert.equal(state.pending, true);
  assert.deepEqual(opened, []);
  releases[1]!({ id: "new" });
  await current;
  assert.deepEqual(opened, ["new"]);
  assert.equal(state.createdId, "new");
});
