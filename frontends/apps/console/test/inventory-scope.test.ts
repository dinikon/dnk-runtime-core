import assert from "node:assert/strict";
import test from "node:test";
import { createRenderer, h, nextTick, ref } from "vue";
import { QueryClient, VueQueryPlugin } from "@tanstack/vue-query";
import { inventoryItemKeys } from "../src/modules/inventory/model/inventory-item.query-keys.ts";
import { useScopedQueryCache } from "../src/shared/model/use-scoped-query-cache.ts";
import type { InventoryScope } from "../src/modules/inventory/model/inventory-item.types.ts";

test("inventory query keys snapshot all request parameters and identity fields", () => {
  const scope: InventoryScope = ["tenant-a", "user-a", "1"];
  const params = { search: "sku", offset: 0, limit: 50 };
  const key = inventoryItemKeys.list(scope, params);
  params.offset = 50;
  assert.equal(key[6].offset, 0);
  for (const other of [
    inventoryItemKeys.list(scope, params),
    inventoryItemKeys.list(["tenant-b", "user-a", "1"], key[6]),
    inventoryItemKeys.list(["tenant-a", "user-b", "1"], key[6]),
    inventoryItemKeys.list(["tenant-a", "user-a", "2"], key[6]),
    inventoryItemKeys.list(scope, { ...key[6], search: "other" }),
    inventoryItemKeys.list(scope, { ...key[6], limit: 100 }),
  ]) {
    assert.notDeepEqual(other, key);
  }
});

test("scope transition cancels old reads and removes old cache while retaining the new identity", async () => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const scope = ref<InventoryScope>(["tenant-a", "user-a", "0"]);
  const params = { search: "", offset: 0, limit: 50 };
  const previousKey = inventoryItemKeys.list(scope.value, params);
  const newKey = inventoryItemKeys.list(["tenant-b", "user-a", "0"], params);
  client.setQueryData(newKey, { items: ["new tenant"] });
  const renderer = createRenderer<object, object>({
    patchProp() {},
    insert() {},
    remove() {},
    setText() {},
    setElementText() {},
    createElement: () => ({}),
    createText: () => ({}),
    createComment: () => ({}),
    parentNode: () => null,
    nextSibling: () => null,
  });
  const app = renderer.createApp({
    setup() {
      useScopedQueryCache(scope, "inventory");
      return () => h("div");
    },
  });
  app.use(VueQueryPlugin, { queryClient: client });
  app.mount({});
  let signal!: AbortSignal;
  let complete!: (value: string) => void;
  const request = client
    .fetchQuery({
      queryKey: previousKey,
      queryFn: (context) => {
        signal = context.signal;
        return new Promise<string>((resolve) => {
          complete = resolve;
        });
      },
    })
    .catch(() => undefined);
  try {
    scope.value = ["tenant-b", "user-a", "0"];
    await nextTick();
    assert.equal(signal.aborted, true);
    complete("late old response");
    await request;
    assert.equal(client.getQueryData(previousKey), undefined);
    assert.deepEqual(client.getQueryData(newKey), { items: ["new tenant"] });
    const oldSessionKey = newKey;
    scope.value = ["tenant-b", "user-a", "1"];
    await nextTick();
    assert.equal(client.getQueryData(oldSessionKey), undefined);
  } finally {
    app.unmount();
    client.clear();
  }
});

test("detail and UOM keys isolate identity and clear together with pending mutations", async () => {
  const client = new QueryClient();
  const scope = ref<InventoryScope>(["tenant-a", "user-a", "1"]);
  const oldDetail = inventoryItemKeys.detail(scope.value, "item-a");
  const oldUoms = inventoryItemKeys.uoms(scope.value);
  assert.notDeepEqual(
    oldDetail,
    inventoryItemKeys.detail(scope.value, "item-b"),
  );
  const renderer = createRenderer<object, object>({
    patchProp() {},
    insert() {},
    remove() {},
    setText() {},
    setElementText() {},
    createElement: () => ({}),
    createText: () => ({}),
    createComment: () => ({}),
    parentNode: () => null,
    nextSibling: () => null,
  });
  const app = renderer.createApp({
    setup() {
      useScopedQueryCache(scope, "inventory");
      return () => h("div");
    },
  });
  app.use(VueQueryPlugin, { queryClient: client });
  app.mount({});
  try {
    client.setQueryData(oldDetail, { sku: "old sku" });
    client.setQueryData(oldUoms, [{ code: "PCS" }]);
    client
      .getMutationCache()
      .build(client, {
        mutationKey: inventoryItemKeys.settings(scope.value),
        mutationFn: async () => "saved",
      });
    const next: InventoryScope = ["tenant-a", "user-a", "2"];
    const newDetail = inventoryItemKeys.detail(next, "item-a");
    client.setQueryData(newDetail, { sku: "new sku" });
    scope.value = next;
    await nextTick();
    assert.equal(client.getQueryData(oldDetail), undefined);
    assert.equal(client.getQueryData(oldUoms), undefined);
    assert.equal(client.getMutationCache().getAll().length, 0);
    assert.deepEqual(client.getQueryData(newDetail), { sku: "new sku" });
  } finally {
    app.unmount();
    client.clear();
  }
});
