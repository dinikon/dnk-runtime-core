import assert from "node:assert/strict";
import test from "node:test";
import { createRenderer, h, effectScope, nextTick, ref } from "vue";
import { createRouter, createMemoryHistory } from "vue-router";
import {
  itemPackagingFromDto,
  itemPackagingCreateToDto,
  itemPackagingPatchToDto,
  itemPackagingsPageFromDto,
  itemPackagingsParamsToDto,
} from "../src/modules/inventory/api/item-packaging.mapper.ts";
import {
  ItemPackagingDraft,
  itemPackagingChanges,
} from "../src/modules/inventory/model/item-packaging-draft.ts";
import { useItemPackagingDraft } from "../src/modules/inventory/model/use-item-packaging-draft.ts";
import {
  positivePackagingQuantity,
  validateItemPackaging,
} from "../src/modules/inventory/model/item-packaging.validation.ts";
import { itemPackagingKeys } from "../src/modules/inventory/model/item-packaging.query-keys.ts";
import { packagingTypeKeys } from "../src/modules/inventory/model/packaging-type.query-keys.ts";
import {
  parseItemPackagingsParams,
  itemPackagingsListParams,
  itemPackagingsUrlParams,
} from "../src/modules/inventory/model/item-packagings-page-state.ts";
import { useItemPackagingsPageState } from "../src/modules/inventory/model/use-item-packagings-page-state.ts";
import {
  itemPackagingsLocation,
  itemPackagingEditLocation,
  itemPackagingReturnPath,
  itemPackagingsReturnPath,
} from "../src/modules/inventory/model/item-packaging-navigation.ts";
import {
  ItemPackagingRequestError,
  retryItemPackagings,
} from "../src/modules/inventory/model/item-packaging.errors.ts";
import type { ItemPackagingValues } from "../src/modules/inventory/model/item-packaging.types.ts";
import type { InventoryScope } from "../src/modules/inventory/model/inventory-scope.types.ts";
const defaults: ItemPackagingValues = {
  packagingTypeId: "type",
  code: "BOX",
  name: "Ящик",
  contentQuantity: "12.123456789012345678901234567890123456789",
  contentUom: "KG",
};
const dto = {
  id: "p",
  inventory_item_id: "sku",
  packaging_type_id: "type",
  code: "BOX",
  name: "Ящик",
  content_quantity: defaults.contentQuantity,
  content_uom: "KG",
};

test("DTOs preserve exact quantity strings and ownership, creation sends only manual values", () => {
  const model = itemPackagingFromDto(dto);
  assert.deepEqual(model, { ...defaults, id: "p", inventoryItemId: "sku" });
  assert.deepEqual(itemPackagingCreateToDto({ ...defaults, code: " BOX " }), {
    packaging_type_id: "type",
    code: " BOX ",
    name: "Ящик",
    content_quantity: defaults.contentQuantity,
    content_uom: "KG",
  });
  assert.deepEqual(
    itemPackagingsPageFromDto({
      items: [dto],
      total: 5,
      offset: 20,
      limit: 20,
    }),
    { items: [model], total: 5, offset: 20, limit: 20 },
  );
});
test("PATCH sends only changed fields, including string zero for Domain and exact case", () => {
  assert.deepEqual(
    itemPackagingPatchToDto(
      itemPackagingChanges(
        { ...defaults, code: "box", contentQuantity: "0" },
        defaults,
      ),
    ),
    { code: "box", content_quantity: "0" },
  );
  assert.deepEqual(
    itemPackagingPatchToDto({ contentQuantity: "500", contentUom: "ML" }),
    { content_quantity: "500", content_uom: "ML" },
  );
  assert.deepEqual(itemPackagingPatchToDto({ packagingTypeId: "other" }), {
    packaging_type_id: "other",
  });
  assert.deepEqual(
    itemPackagingPatchToDto(itemPackagingChanges(defaults, defaults)),
    {},
  );
});
test("quantity input supports exact decimal and exponents without Number rounding", () => {
  for (const value of [
    defaults.contentQuantity,
    "1e-1000",
    "+0.0001",
    ".5",
    "500.",
    "1e1000",
    "000.00001",
  ])
    assert.equal(positivePackagingQuantity(value), true, value);
  for (const value of [
    "",
    " ",
    "0",
    "0e99",
    "0.0",
    "-1",
    "NaN",
    "Infinity",
    "1,5",
    "1e",
    "1e1.5",
  ])
    assert.equal(positivePackagingQuantity(value), false, value);
});
test("validation assists required fields and compatible units while Domain owns step conversion", () => {
  const units = [{ code: "KG", dimension: "MASS" as const }];
  assert.deepEqual(validateItemPackaging(defaults, units), {});
  assert.deepEqual(
    Object.keys(
      validateItemPackaging(
        {
          packagingTypeId: "",
          code: " ",
          name: "",
          contentQuantity: "0",
          contentUom: "L",
        },
        units,
      ),
    ).sort(),
    ["code", "contentQuantity", "contentUom", "name", "packagingTypeId"],
  );
  assert.deepEqual(
    validateItemPackaging({ ...defaults, contentQuantity: "0.123" }, units),
    {},
  );
});
test("literal search and pagination round trip, oversized offsets stay in backend range", () => {
  const state = parseItemPackagingsParams({
    search: " BOX%_ ",
    page: "3",
    limit: "20",
  });
  assert.deepEqual(state, { search: "BOX%_", page: 3, limit: 20 });
  assert.deepEqual(itemPackagingsParamsToDto(itemPackagingsListParams(state)), {
    search: "BOX%_",
    offset: 40,
    limit: 20,
  });
  assert.deepEqual(
    parseItemPackagingsParams(itemPackagingsUrlParams(state)),
    state,
  );
  assert.deepEqual(
    parseItemPackagingsParams({ search: [], page: "-5", limit: "1000" }),
    { search: "", page: 1, limit: 50 },
  );
  assert.ok(
    itemPackagingsListParams(parseItemPackagingsParams({ page: "1e100" }))
      .offset <= 2147483647,
  );
});
test("keys isolate every identity, owner and packaging and separate candidate infinite cache", () => {
  const scope: InventoryScope = ["tenant", "user", "1"],
    params = { search: "A", offset: 0, limit: 50 };
  const key = itemPackagingKeys.list(scope, "sku", params);
  params.offset = 50;
  assert.equal(key[7].offset, 0);
  for (const other of [
    itemPackagingKeys.list(["other", "user", "1"], "sku", key[7]),
    itemPackagingKeys.list(["tenant", "other", "1"], "sku", key[7]),
    itemPackagingKeys.list(["tenant", "user", "2"], "sku", key[7]),
    itemPackagingKeys.list(scope, "other", key[7]),
    itemPackagingKeys.list(scope, "sku", params),
  ])
    assert.notDeepEqual(key, other);
  assert.notDeepEqual(
    itemPackagingKeys.detail(scope, "sku", "a"),
    itemPackagingKeys.detail(scope, "sku", "b"),
  );
  assert.notDeepEqual(
    itemPackagingKeys.update(scope, "sku", "a"),
    itemPackagingKeys.update(scope, "other", "a"),
  );
  assert.notDeepEqual(
    packagingTypeKeys.candidates(scope, "A"),
    packagingTypeKeys.list(scope, {
      search: "A",
      offset: 0,
      limit: 20,
      isActive: true,
    }),
  );
  assert.equal(packagingTypeKeys.candidates(scope, "A")[6].isActive, true);
});
test("draft preserves dirty refetch and newer typing during canonical save acknowledgement", () => {
  const draft = new ItemPackagingDraft();
  draft.receive(defaults);
  const sent = {
    ...defaults,
    code: " CAN ",
    packagingTypeId: "new",
    contentQuantity: "500",
    contentUom: "G",
  };
  draft.change(sent);
  draft.receive({ ...defaults, name: "External" });
  assert.deepEqual(draft.values, sent);
  draft.change({
    ...sent,
    name: "Newer",
    contentQuantity: "600",
    packagingTypeId: "newer",
  });
  draft.acknowledge(sent, { ...sent, code: "CAN" });
  assert.deepEqual(draft.changes, {
    packagingTypeId: "newer",
    name: "Newer",
    contentQuantity: "600",
  });
  assert.equal(draft.values?.contentUom, "G");
  assert.equal(draft.values?.code, "CAN");
  draft.reset(defaults);
  assert.equal(draft.dirty, false);
  draft.clear();
  assert.equal(draft.values, null);
});
test("draft incorporates independent server values only where input still matches sent snapshot", () => {
  const draft = new ItemPackagingDraft();
  draft.receive(defaults);
  const sent = { ...defaults, name: "Sent" };
  draft.change(sent);
  draft.acknowledge(sent, { ...sent, contentUom: "G" });
  assert.equal(draft.values?.contentUom, "G");
  assert.equal(draft.dirty, false);
});
test("draft clears on session or owner change and ignores pending refetch", async () => {
  const effects = effectScope(),
    identity = ref("a:sku:p"),
    pending = ref(false),
    source = ref<ItemPackagingValues | undefined>(defaults);
  const draft = effects.run(() =>
    useItemPackagingDraft(() => source.value, identity, pending),
  )!;
  try {
    draft.change({ ...defaults, name: "Dirty" });
    pending.value = true;
    source.value = { ...defaults, name: "External" };
    assert.equal(draft.values.value?.name, "Dirty");
    identity.value = "b:sku:p";
    source.value = undefined;
    pending.value = false;
    await nextTick();
    assert.equal(draft.values.value, null);
    source.value = defaults;
    await nextTick();
    assert.equal(draft.dirty.value, false);
  } finally {
    effects.stop();
  }
});
test("return paths keep exact owner context and nested Catalog return without external URLs", () => {
  const sku = "sku-id",
    origin = `/inventory/items/${sku}?returnTo=${encodeURIComponent("/catalog/items/catalog?locale=ru")}`;
  assert.equal(itemPackagingsReturnPath(sku, origin), origin);
  const list = `/inventory/items/${sku}/packagings?search=A&page=3&returnTo=${encodeURIComponent(origin)}#table`;
  assert.equal(itemPackagingReturnPath(sku, list), list);
  assert.deepEqual(itemPackagingsLocation(sku, origin), {
    name: "inventory-item-packagings",
    params: { inventoryItemId: sku },
    query: { returnTo: origin },
  });
  assert.deepEqual(itemPackagingEditLocation(sku, "p", list), {
    name: "inventory-item-packaging-edit",
    params: { inventoryItemId: sku, packagingId: "p" },
    query: { returnTo: list },
  });
  for (const invalid of [
    undefined,
    "https://evil.test",
    "//evil.test",
    `/inventory/items/other/packagings`,
    `${list}\\bad`,
    `${list}\n`,
  ])
    assert.equal(
      itemPackagingReturnPath(sku, invalid),
      `/inventory/items/${sku}/packagings`,
    );
  assert.equal(
    itemPackagingsReturnPath(sku, "/inventory/items/other"),
    `/inventory/items/${sku}`,
  );
});
test("409 remains an operation error and ambiguous writes cannot trigger automatic retry", () => {
  const conflict = new ItemPackagingRequestError("Inactive type", 409);
  assert.deepEqual(conflict.fields, {});
  for (const status of [403, 404, 409, 422])
    assert.equal(
      retryItemPackagings(0, new ItemPackagingRequestError("Rejected", status)),
      false,
    );
  for (const status of [null, 408, 500, 503])
    assert.equal(
      new ItemPackagingRequestError("Unknown", status).uncertain,
      true,
    );
  assert.equal(retryItemPackagings(0, new Error("network")), true);
  assert.equal(retryItemPackagings(1, new Error("network")), false);
});
test("URL controller applies pending search, preserves unrelated values and disposes timers", async () => {
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
    owner = ref("sku");
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/:pathMatch(.*)*", component: { render: () => null } }],
  });
  await router.push("/inventory/items/sku/packagings?custom=keep&page=3#table");
  let state!: ReturnType<typeof useItemPackagingsPageState>;
  const app = renderer.createApp({
    setup() {
      state = useItemPackagingsPageState(scope, owner);
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
    state.setSearch(" BOX ");
    state.setPagination({ page: 3, limit: 20 });
    await flush();
    assert.equal(state.params.value.page, 1);
    assert.equal(state.params.value.search, "BOX");
    assert.equal(router.currentRoute.value.query.custom, "keep");
    assert.equal(router.currentRoute.value.hash, "#table");
    state.setPagination({ page: 2, limit: 20 });
    await flush();
    assert.equal(state.listParams.value.offset, 20);
    state.setSearch("cancelled");
    state.cancelSearch();
    await new Promise((resolve) => setTimeout(resolve, 350));
    assert.equal(state.params.value.search, "BOX");
    state.reconcilePage(20);
    await flush();
    assert.equal(state.params.value.page, 1);
    assert.equal(state.params.value.search, "BOX");
    assert.equal(router.currentRoute.value.query.custom, "keep");
    assert.equal(router.currentRoute.value.hash, "#table");
    state.reconcilePage(0);
    await flush();
    assert.equal(state.params.value.page, 1);
    state.setSearch("old");
    owner.value = "new";
    await flush();
    assert.equal(state.searchText.value, "");
    assert.equal(state.params.value.page, 1);
    state.searchAll("box");
    await flush();
    assert.equal(state.params.value.search, "box");
    scope.value = ["other", "user", "2"];
    await flush();
    assert.equal(state.params.value.search, "");
    state.setSearch("disposed");
    app.unmount();
    mounted = false;
    await new Promise((resolve) => setTimeout(resolve, 350));
    assert.equal(router.currentRoute.value.query.search, undefined);
  } finally {
    if (mounted) app.unmount();
  }
});
