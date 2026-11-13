import assert from "node:assert/strict";
import test from "node:test";
import { createRenderer, h, nextTick, ref, effectScope } from "vue";
import { createRouter, createMemoryHistory } from "vue-router";
import {
  stockLocationFromDto,
  stockLocationCreateToDto,
  stockLocationPatchToDto,
  stockLocationsParamsToDto,
  stockLocationsPageFromDto,
} from "../src/modules/inventory/api/stock-location.mapper.ts";
import {
  parseStockLocationsParams,
  stockLocationsListParams,
  stockLocationsUrlParams,
} from "../src/modules/inventory/model/stock-locations-page-state.ts";
import { stockLocationKeys } from "../src/modules/inventory/model/stock-location.query-keys.ts";
import {
  StockLocationDraft,
  stockLocationChanges,
} from "../src/modules/inventory/model/stock-location-draft.ts";
import { useStockLocationDraft } from "../src/modules/inventory/model/use-stock-location-draft.ts";
import {
  useStockLocationsPageState,
  type StockLocationsPageState,
} from "../src/modules/inventory/model/use-stock-locations-page-state.ts";
import {
  stockLocationsLocation,
  stockLocationEditLocation,
  stockLocationsReturnPath,
  warehouseLocationsReturnPath,
} from "../src/modules/inventory/model/stock-location-navigation.ts";
import {
  validateStockLocation,
  validateStockLocationCreate,
} from "../src/modules/inventory/model/stock-location-form.validation.ts";
import {
  StockLocationRequestError,
  retryStockLocations,
} from "../src/modules/inventory/model/stock-location.errors.ts";
import type { StockLocationEditValues } from "../src/modules/inventory/model/stock-location.types.ts";
import type { InventoryScope } from "../src/modules/inventory/model/inventory-scope.types.ts";

const wh = "155bd021-244b-4c33-bc46-7b1abb87f556",
  parent = "155bd021-244b-4c33-bc46-7b1abb87f557";
const defaults: StockLocationEditValues = {
  code: "main",
  name: "Main",
  isActive: true,
};

test("stock location DTO mapping preserves parent, local false, type and list metadata", () => {
  const dto = {
    id: "loc",
    warehouse_id: wh,
    parent_location_id: parent,
    code: "a",
    name: "A",
    location_type: "RECEIVING" as const,
    is_active: false,
  };
  assert.deepEqual(stockLocationFromDto(dto), {
    id: "loc",
    warehouseId: wh,
    parentLocationId: parent,
    code: "a",
    name: "A",
    locationType: "RECEIVING",
    isActive: false,
  });
  assert.equal(
    stockLocationFromDto({ ...dto, parent_location_id: null }).parentLocationId,
    null,
  );
  assert.deepEqual(
    stockLocationsPageFromDto({
      items: [dto],
      total: 12,
      offset: 20,
      limit: 20,
    }),
    { items: [stockLocationFromDto(dto)], total: 12, offset: 20, limit: 20 },
  );
  assert.deepEqual(
    stockLocationCreateToDto({
      code: " Straße ",
      name: " Name ",
      locationType: "STORAGE",
      parentLocationId: null,
    }),
    {
      code: " Straße ",
      name: " Name ",
      location_type: "STORAGE",
      parent_location_id: null,
    },
  );
  assert.equal(
    stockLocationCreateToDto({
      code: "a",
      name: "A",
      locationType: "TRANSIT",
      parentLocationId: parent,
    }).parent_location_id,
    parent,
  );
});

test("changed-only PATCH includes false, omits immutable fields and skips empty changes", () => {
  assert.deepEqual(
    stockLocationPatchToDto(
      stockLocationChanges({ ...defaults, isActive: false }, defaults),
    ),
    { is_active: false },
  );
  assert.deepEqual(stockLocationPatchToDto({ name: "New" }), { name: "New" });
  assert.deepEqual(
    stockLocationPatchToDto(stockLocationChanges(defaults, defaults)),
    {},
  );
});

test("list payload preserves literal search and inactive filter; no parent means all levels", () => {
  assert.deepEqual(
    stockLocationsParamsToDto({
      search: "Straße%_",
      isActive: false,
      locationType: "QUARANTINE",
      parentLocationId: parent,
      offset: 20,
      limit: 20,
    }),
    {
      search: "Straße%_",
      is_active: false,
      location_type: "QUARANTINE",
      parent_location_id: parent,
      offset: 20,
      limit: 20,
    },
  );
  assert.deepEqual(
    stockLocationsParamsToDto({
      search: "",
      isActive: null,
      locationType: null,
      parentLocationId: null,
      offset: 0,
      limit: 50,
    }),
    { offset: 0, limit: 50 },
  );
});

test("URL state normalizes unknown filters and bounds offset to the backend range", () => {
  const params = parseStockLocationsParams({
    search: " Київ ",
    is_active: "false",
    location_type: "STORAGE",
    parent_location_id: parent.toUpperCase(),
    page: "3",
    limit: "20",
  });
  assert.equal(params.parentLocationId, parent);
  assert.deepEqual(stockLocationsListParams(params), {
    search: "Київ",
    isActive: false,
    locationType: "STORAGE",
    parentLocationId: parent,
    offset: 40,
    limit: 20,
  });
  assert.deepEqual(
    parseStockLocationsParams(stockLocationsUrlParams(params)),
    params,
  );
  assert.deepEqual(
    parseStockLocationsParams({
      search: [],
      is_active: "yes",
      location_type: "bad",
      parent_location_id: "bad",
      page: "-2",
      limit: "999",
    }),
    {
      search: "",
      activity: "all",
      locationType: null,
      parentLocationId: null,
      page: 1,
      limit: 50,
    },
  );
  assert.ok(
    stockLocationsListParams(parseStockLocationsParams({ page: "1e100" }))
      .offset <= 2_147_483_647,
  );
});

test("stock location keys snapshot filters and isolate warehouse, location and every identity field", () => {
  const scope: InventoryScope = ["tenant", "user", "1"];
  const params = {
    search: "a",
    isActive: false,
    locationType: "STORAGE" as const,
    parentLocationId: parent,
    offset: 0,
    limit: 50,
  };
  const key = stockLocationKeys.list(scope, wh, params);
  params.offset = 50;
  assert.equal(key[7].offset, 0);
  for (const other of [
    stockLocationKeys.list(["other", "user", "1"], wh, key[7]),
    stockLocationKeys.list(["tenant", "other", "1"], wh, key[7]),
    stockLocationKeys.list(["tenant", "user", "2"], wh, key[7]),
    stockLocationKeys.list(scope, "other", key[7]),
    stockLocationKeys.list(scope, wh, { ...key[7], parentLocationId: null }),
    stockLocationKeys.list(scope, wh, params),
  ])
    assert.notDeepEqual(key, other);
  assert.notDeepEqual(
    stockLocationKeys.detail(scope, wh, "a"),
    stockLocationKeys.detail(scope, wh, "b"),
  );
  assert.notDeepEqual(
    stockLocationKeys.parents(scope, wh, "a"),
    stockLocationKeys.parents(scope, wh, "b"),
  );
  assert.equal(stockLocationKeys.parents(scope, wh, "a")[7].isActive, null);
  assert.equal(stockLocationKeys.parents(scope, wh, "a")[7].locationType, null);
});

test("draft preserves new typing and refetch, acknowledges only sent values", () => {
  const draft = new StockLocationDraft();
  draft.receive(defaults);
  const sent = { ...defaults, code: " NEW ", isActive: false };
  draft.change(sent);
  draft.receive({ ...defaults, name: "External" });
  assert.deepEqual(draft.values, sent);
  draft.change({ ...sent, name: "Newer", isActive: true });
  draft.acknowledge(sent, { ...sent, code: "new" });
  assert.deepEqual(draft.values, {
    code: "new",
    name: "Newer",
    isActive: true,
  });
  assert.deepEqual(draft.changes, { name: "Newer", isActive: true });
  draft.reset(defaults);
  assert.equal(draft.dirty, false);
  draft.clear();
  assert.equal(draft.values, null);
});

test("partial response merges server changes for fields that were not edited while saving", () => {
  const draft = new StockLocationDraft();
  draft.receive(defaults);
  const sent = { ...defaults, code: "new" };
  draft.change(sent);
  draft.acknowledge(sent, { ...sent, name: "External" });
  assert.equal(draft.values?.name, "External");
  assert.equal(draft.dirty, false);
});

test("draft resets on warehouse/context change and ignores pending refetch", async () => {
  const effects = effectScope(),
    identity = ref("warehouse-a:loc"),
    pending = ref(false),
    source = ref<StockLocationEditValues | undefined>(defaults);
  const draft = effects.run(() =>
    useStockLocationDraft(() => source.value, identity, pending),
  )!;
  try {
    draft.change({ ...defaults, name: "Edited" });
    pending.value = true;
    source.value = { ...defaults, name: "Refetched" };
    assert.equal(draft.values.value?.name, "Edited");
    identity.value = "warehouse-b:loc";
    source.value = undefined;
    pending.value = false;
    await nextTick();
    assert.equal(draft.values.value, null);
    source.value = { ...defaults, name: "New context" };
    assert.equal(draft.values.value?.name, "New context");
  } finally {
    effects.stop();
  }
});

test("navigation preserves exact same-warehouse context and rejects external or unrelated return paths", () => {
  const path = `/inventory/warehouses/${wh}/locations?search=a&is_active=false&page=2#table`;
  assert.equal(stockLocationsReturnPath(wh, path), path);
  const warehousePath = `/inventory/warehouses/${wh}?returnTo=/inventory/warehouses?page=2`;
  assert.equal(warehouseLocationsReturnPath(wh, warehousePath), warehousePath);
  assert.equal(
    warehouseLocationsReturnPath(wh, "/inventory/warehouses?page=3"),
    "/inventory/warehouses?page=3",
  );
  assert.deepEqual(stockLocationsLocation(wh, warehousePath), {
    name: "inventory-stock-locations",
    params: { warehouseId: wh },
    query: { returnTo: warehousePath },
  });
  assert.deepEqual(stockLocationEditLocation(wh, "id", path), {
    name: "inventory-stock-location-edit",
    params: { warehouseId: wh, locationId: "id" },
    query: { returnTo: path },
  });
  for (const invalid of [
    undefined,
    "https://evil.test",
    "//evil.test",
    `/inventory/warehouses/${parent}/locations`,
    `${path}\\bad`,
    `${path}\n`,
  ])
    assert.equal(
      stockLocationsReturnPath(wh, invalid),
      `/inventory/warehouses/${wh}/locations`,
    );
});

test("form validation assists mandatory input without replacing Domain normalization", () => {
  assert.deepEqual(
    validateStockLocation({ code: " Straße ", name: " Name " }),
    {},
  );
  assert.deepEqual(
    Object.keys(
      validateStockLocationCreate({
        code: " ",
        name: "",
        locationType: "",
        parentLocationId: null,
      }),
    ).sort(),
    ["code", "locationType", "name"],
  );
});

test("conflicts stay operation errors and writes never trigger automatic retry", () => {
  const conflict = new StockLocationRequestError(
    "Основную STORAGE нельзя деактивировать",
    409,
  );
  assert.deepEqual(conflict.fields, {});
  assert.equal(conflict.uncertain, false);
  for (const status of [403, 404, 409, 422])
    assert.equal(
      retryStockLocations(0, new StockLocationRequestError("Rejected", status)),
      false,
    );
  assert.equal(retryStockLocations(0, new Error("network")), true);
  assert.equal(retryStockLocations(1, new Error("network")), false);
  for (const status of [null, 408, 500])
    assert.equal(
      new StockLocationRequestError("Unknown result", status).uncertain,
      true,
    );
});

test("page state keeps filters in URL, shows children atomically and clears context-specific parents", async () => {
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
  const scope = ref<InventoryScope>(["tenant", "user", "1"]),
    warehouseId = ref(wh);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/:pathMatch(.*)*", component: { render: () => null } }],
  });
  await router.push(
    `/inventory/warehouses/${wh}/locations?custom=keep&is_active=false&location_type=STORAGE&page=3#table`,
  );
  let state!: StockLocationsPageState;
  const app = renderer.createApp({
    setup() {
      state = useStockLocationsPageState(scope, warehouseId);
      return () => h("div");
    },
  });
  app.use(router);
  app.mount({});
  const flush = async (): Promise<void> => {
    await new Promise((resolve) => setTimeout(resolve, 0));
    await nextTick();
  };
  let mounted = true;
  try {
    state.showChildren(parent);
    await flush();
    assert.equal(router.currentRoute.value.query.parent_location_id, parent);
    assert.equal(router.currentRoute.value.query.is_active, undefined);
    assert.equal(router.currentRoute.value.query.page, undefined);
    assert.equal(router.currentRoute.value.query.custom, "keep");
    assert.equal(router.currentRoute.value.hash, "#table");
    state.setActivity("inactive");
    await flush();
    state.setPagination({ page: 2, limit: 20 });
    await flush();
    assert.equal(state.listParams.value.isActive, false);
    assert.equal(state.listParams.value.parentLocationId, parent);
    assert.equal(state.params.value.page, 1);
    state.searchAll("new");
    await flush();
    assert.equal(state.params.value.parentLocationId, null);
    assert.equal(state.params.value.locationType, null);
    assert.equal(state.params.value.activity, "all");
    state.setParent(parent);
    await flush();
    scope.value = ["tenant", "user", "2"];
    await flush();
    assert.equal(state.params.value.parentLocationId, null);
    assert.equal(state.searchText.value, "");
    state.setSearch("disposed");
    app.unmount();
    mounted = false;
    await new Promise((resolve) => setTimeout(resolve, 350));
    assert.equal(router.currentRoute.value.query.search, undefined);
  } finally {
    if (mounted) app.unmount();
  }
});
