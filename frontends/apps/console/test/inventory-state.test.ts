import assert from "node:assert/strict";
import test from "node:test";
import { setImmediate as settle } from "node:timers/promises";
import { createRenderer, h, nextTick, ref, type Ref } from "vue";
import { createRouter, createMemoryHistory, type Router } from "vue-router";
import {
  inventoryItemsListParams,
  inventoryItemsUrlParams,
  parseInventoryItemsParams,
} from "../src/modules/inventory/model/inventory-items-page-state.ts";
import { useInventoryItemsPageState } from "../src/modules/inventory/model/use-inventory-items-page-state.ts";
import type { InventoryScope } from "../src/modules/inventory/model/inventory-scope.types.ts";

test("inventory URL values are bounded, scalar and canonical", () => {
  for (const value of [undefined, "NaN", "Infinity", "", "-5", ["2"], null]) {
    assert.equal(parseInventoryItemsParams({ page: value }).page, 1);
  }
  assert.deepEqual(
    parseInventoryItemsParams({ search: ["bad"], page: "2.9", limit: "20" }),
    { search: "", page: 2, limit: 20 },
  );
  assert.deepEqual(
    parseInventoryItemsParams({ search: " Straße ", limit: "999" }),
    { search: "Straße", page: 1, limit: 50 },
  );
  const huge = parseInventoryItemsParams({
    page: "999999999999999999999",
    limit: "100",
  });
  assert.ok(inventoryItemsListParams(huge).offset <= 2147483600);
  assert.deepEqual(
    inventoryItemsUrlParams({ page: 1, search: "", limit: 50 }),
    { page: undefined, search: undefined, limit: undefined },
  );
});

async function mountState(
  url: string,
  scope: Ref<InventoryScope> = ref(["tenant-a", "user-a", "0"]),
): Promise<{
  state: ReturnType<typeof useInventoryItemsPageState>;
  router: Router;
  unmount: () => void;
}> {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/:pathMatch(.*)*", component: { render: () => null } }],
  });
  await router.push(url);
  let state!: ReturnType<typeof useInventoryItemsPageState>;
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
      state = useInventoryItemsPageState(scope);
      return () => h("div");
    },
  });
  app.use(router);
  app.mount({});
  await nextTick();
  return { state, router, unmount: () => app.unmount() };
}

async function navigate(router: Router, action: () => void): Promise<void> {
  await new Promise<void>((resolve) => {
    const stop = router.afterEach(() => {
      stop();
      resolve();
    });
    action();
  });
  await nextTick();
}

test("inventory search and pagination preserve unrelated URL state and restore on back/reload", async () => {
  const fixture = await mountState(
    "/inventory/items?search=old&page=3&limit=20&keep=yes#list",
  );
  const { state, router } = fixture;
  try {
    assert.deepEqual(state.listParams.value, {
      search: "old",
      offset: 40,
      limit: 20,
    });
    await navigate(router, () => state.setPagination({ page: 4, limit: 20 }));
    assert.equal(state.params.value.page, 4);
    await navigate(router, () => router.back());
    assert.equal(state.params.value.page, 3);
    await navigate(router, () => {
      state.setSearch(" new SKU ");
      state.submitSearch();
    });
    assert.deepEqual(state.listParams.value, {
      search: "new SKU",
      offset: 0,
      limit: 20,
    });
    await navigate(router, () => state.setPagination({ page: 2, limit: 100 }));
    assert.deepEqual(state.params.value, {
      search: "new SKU",
      page: 1,
      limit: 100,
    });
    await navigate(router, state.clearSearch);
    assert.deepEqual(router.currentRoute.value.query, {
      limit: "100",
      keep: "yes",
    });
    assert.equal(router.currentRoute.value.hash, "#list");
    const reloaded = await mountState(router.currentRoute.value.fullPath);
    assert.deepEqual(reloaded.state.params.value, state.params.value);
    reloaded.unmount();
  } finally {
    fixture.unmount();
  }
});

test("debounce commits the latest search only and disposal cancels a pending search", async (context) => {
  context.mock.timers.enable({ apis: ["setTimeout"] });
  const fixture = await mountState("/inventory/items?page=2");
  try {
    fixture.state.setSearch("first");
    context.mock.timers.tick(200);
    fixture.state.setSearch("second");
    context.mock.timers.tick(299);
    assert.equal(fixture.router.currentRoute.value.query.search, undefined);
    await navigate(fixture.router, () => context.mock.timers.tick(1));
    assert.equal(fixture.state.params.value.search, "second");
    assert.equal(fixture.state.params.value.page, 1);
    fixture.state.setSearch("unmounted");
    fixture.unmount();
    const afterUnmount = fixture.router.currentRoute.value.fullPath;
    context.mock.timers.tick(500);
    await settle();
    assert.equal(fixture.router.currentRoute.value.fullPath, afterUnmount);
  } finally {
    fixture.unmount();
  }
});

test("scope changes clear pending input and old filters without clearing an initial deep link", async (context) => {
  context.mock.timers.enable({ apis: ["setTimeout"] });
  const scope = ref<InventoryScope>([null, "user-a", "0"]);
  const fixture = await mountState(
    "/inventory/items?search=deep&page=2&keep=yes",
    scope,
  );
  try {
    scope.value = ["tenant-a", "user-a", "0"];
    await nextTick();
    assert.equal(fixture.state.params.value.search, "deep");
    fixture.state.setSearch("private-draft");
    await navigate(fixture.router, () => {
      scope.value = ["tenant-b", "user-a", "0"];
    });
    assert.equal(fixture.state.searchText.value, "");
    assert.equal(fixture.state.params.value.search, "");
    assert.equal(fixture.state.params.value.page, 1);
    context.mock.timers.tick(500);
    await nextTick();
    assert.equal(fixture.router.currentRoute.value.query.search, undefined);
    assert.equal(fixture.router.currentRoute.value.query.keep, "yes");
  } finally {
    fixture.unmount();
  }
});
