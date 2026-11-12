import assert from "node:assert/strict";
import test from "node:test";
import { effectScope, nextTick, ref } from "vue";
import {
  warehouseCreateToDto,
  warehouseFromDto,
  warehousePatchToDto,
  warehousesParamsToDto,
  warehousesPageFromDto,
} from "../src/modules/inventory/api/warehouse.mapper.ts";
import {
  WarehouseDraft,
  warehouseChanges,
} from "../src/modules/inventory/model/warehouse-draft.ts";
import { useWarehouseDraft } from "../src/modules/inventory/model/use-warehouse-draft.ts";
import { warehouseKeys } from "../src/modules/inventory/model/warehouse.query-keys.ts";
import {
  parseWarehousesParams,
  warehousesListParams,
  warehousesUrlParams,
} from "../src/modules/inventory/model/warehouses-page-state.ts";
import {
  warehouseEditLocation,
  warehouseReturnPath,
} from "../src/modules/inventory/model/warehouse-navigation.ts";
import { validateWarehouse } from "../src/modules/inventory/model/warehouse-form.validation.ts";
import {
  WarehouseRequestError,
  retryWarehouses,
} from "../src/modules/inventory/model/warehouse.errors.ts";
import type { WarehouseEditValues } from "../src/modules/inventory/model/warehouse.types.ts";
const defaults: WarehouseEditValues = {
  code: "main",
  name: "Основной склад",
  isActive: true,
};

test("warehouse DTO mapping keeps false and nullable links, creation sends only manual values", () => {
  assert.deepEqual(warehouseCreateToDto({ code: " Straße ", name: " Name " }), {
    code: " Straße ",
    name: " Name ",
  });
  const dto = {
    id: "warehouse",
    code: "main",
    name: "Основной",
    is_active: false,
    default_storage_location_id: null,
  };
  const model = warehouseFromDto(dto);
  assert.deepEqual(model, {
    id: "warehouse",
    code: "main",
    name: "Основной",
    isActive: false,
    defaultStorageLocationId: null,
  });
  assert.equal(
    warehouseFromDto({ ...dto, default_storage_location_id: "location" })
      .defaultStorageLocationId,
    "location",
  );
  assert.deepEqual(
    warehousesPageFromDto({ items: [dto], total: 5, offset: 20, limit: 20 }),
    { items: [model], total: 5, offset: 20, limit: 20 },
  );
});

test("partial PATCH sends changed fields including explicit false without readonly attributes", () => {
  const changes = warehouseChanges({ ...defaults, isActive: false }, defaults);
  assert.deepEqual(warehousePatchToDto(changes), { is_active: false });
  assert.deepEqual(warehousePatchToDto({ name: "New" }), { name: "New" });
  assert.deepEqual(
    warehousePatchToDto(warehouseChanges(defaults, defaults)),
    {},
  );
  assert.deepEqual(
    warehousePatchToDto({ code: "A", name: "B", isActive: true }),
    { code: "A", name: "B", is_active: true },
  );
});

test("list params preserve inactive false and literal Unicode search without client casefold", () => {
  assert.deepEqual(
    warehousesParamsToDto({
      search: " Straße%_ ",
      offset: 0,
      limit: 50,
      isActive: false,
    }),
    { search: " Straße%_ ", offset: 0, limit: 50, is_active: false },
  );
  assert.deepEqual(
    warehousesParamsToDto({ search: "", offset: 0, limit: 50, isActive: null }),
    { offset: 0, limit: 50 },
  );
});

test("URL page state normalizes invalid values and round trips activity, search and pagination", () => {
  const params = parseWarehousesParams({
    search: " Київ ",
    is_active: "false",
    page: "3",
    limit: "20",
  });
  assert.deepEqual(params, {
    search: "Київ",
    activity: "inactive",
    page: 3,
    limit: 20,
  });
  assert.deepEqual(warehousesListParams(params), {
    search: "Київ",
    isActive: false,
    offset: 40,
    limit: 20,
  });
  assert.deepEqual(warehousesUrlParams(params), {
    search: "Київ",
    is_active: "false",
    page: "3",
    limit: "20",
  });
  assert.deepEqual(
    parseWarehousesParams({
      search: [],
      is_active: "yes",
      page: "NaN",
      limit: "999",
    }),
    { search: "", activity: "all", page: 1, limit: 50 },
  );
  assert.equal(parseWarehousesParams({ page: "-5" }).page, 1);
  assert.equal(parseWarehousesParams({ page: "2.9" }).page, 2);
  assert.ok(
    Number.isSafeInteger(
      warehousesListParams(parseWarehousesParams({ page: "1e100" })).offset,
    ),
  );
  assert.equal(
    warehousesUrlParams(parseWarehousesParams({ is_active: "true" })).is_active,
    "true",
  );
});

test("warehouse cache keys snapshot filters and isolate tenant, user, session and entity", () => {
  const params = { search: "a", offset: 0, limit: 50, isActive: false };
  const key = warehouseKeys.list(["tenant", "user", "1"], params);
  params.offset = 50;
  assert.equal(key[6].offset, 0);
  for (const other of [
    warehouseKeys.list(["other", "user", "1"], key[6]),
    warehouseKeys.list(["tenant", "other", "1"], key[6]),
    warehouseKeys.list(["tenant", "user", "2"], key[6]),
    warehouseKeys.list(["tenant", "user", "1"], { ...key[6], isActive: true }),
    warehouseKeys.list(["tenant", "user", "1"], params),
  ])
    assert.notDeepEqual(key, other);
  assert.notDeepEqual(
    warehouseKeys.detail(["tenant", "user", "1"], "a"),
    warehouseKeys.detail(["tenant", "user", "1"], "b"),
  );
  assert.notDeepEqual(
    warehouseKeys.create(["tenant", "user", "1"]),
    warehouseKeys.update(["tenant", "user", "1"]),
  );
});

test("draft ignores background refetch and accepts server canonicalization without erasing newer input", () => {
  const draft = new WarehouseDraft();
  draft.receive(defaults);
  const sent = { ...defaults, code: " NEW ", isActive: false };
  draft.change(sent);
  draft.receive({ ...defaults, name: "External" });
  assert.deepEqual(draft.values, sent);
  draft.change({ ...sent, name: "Typing while saving", isActive: true });
  draft.acknowledge(sent, { ...sent, code: "new" });
  assert.deepEqual(draft.values, {
    code: "new",
    name: "Typing while saving",
    isActive: true,
  });
  assert.deepEqual(draft.changes, {
    name: "Typing while saving",
    isActive: true,
  });
  draft.reset({ ...sent, code: "new" });
  assert.equal(draft.dirty, false);
  draft.clear();
  assert.equal(draft.values, null);
});

test("successful partial response incorporates independent server changes only for untouched inputs", () => {
  const draft = new WarehouseDraft();
  draft.receive(defaults);
  const sent = { ...defaults, code: "renamed" };
  draft.change(sent);
  draft.acknowledge(sent, { ...sent, name: "Name changed on server" });
  assert.equal(draft.values?.name, "Name changed on server");
  assert.equal(draft.dirty, false);
});

test("draft resets with context and defers refetch while a mutation is pending", async () => {
  const effects = effectScope(),
    identity = ref("tenant-a:id"),
    pending = ref(false),
    source = ref<WarehouseEditValues | undefined>(defaults);
  const draft = effects.run(() =>
    useWarehouseDraft(() => source.value, identity, pending),
  )!;
  try {
    draft.change({ ...defaults, isActive: false });
    pending.value = true;
    source.value = { ...defaults, name: "Late refetch" };
    assert.equal(draft.values.value?.name, defaults.name);
    identity.value = "tenant-b:id";
    source.value = undefined;
    pending.value = false;
    await nextTick();
    assert.equal(draft.values.value, null);
    source.value = { ...defaults, name: "New tenant" };
    await nextTick();
    assert.equal(draft.values.value?.name, "New tenant");
    assert.equal(draft.dirty.value, false);
  } finally {
    effects.stop();
  }
});

test("navigation keeps list filters but rejects outside URLs and non-list return paths", () => {
  const path =
    "/inventory/warehouses?search=a&is_active=false&page=2&limit=20#table";
  assert.equal(warehouseReturnPath(path), path);
  assert.deepEqual(warehouseEditLocation("id", path), {
    name: "inventory-warehouse-edit",
    params: { warehouseId: "id" },
    query: { returnTo: path },
  });
  for (const value of [
    undefined,
    "https://evil.test",
    "//evil.test",
    "/inventory/warehouses/other",
    "/inventory/warehouses\\evil",
    "/inventory/warehouses\n",
  ])
    assert.equal(warehouseReturnPath(value), "/inventory/warehouses");
});

test("validation assists input while Domain remains responsible for canonical codes", () => {
  assert.deepEqual(validateWarehouse({ code: " Straße ", name: " Name " }), {});
  assert.deepEqual(
    Object.keys(validateWarehouse({ code: "  ", name: "" })).sort(),
    ["code", "name"],
  );
});

test("write uncertainty never retries automatically; reads do not retry client rejections", () => {
  for (const status of [403, 404, 409, 422]) {
    const error = new WarehouseRequestError("Rejected", status);
    assert.equal(error.uncertain, false);
    assert.equal(retryWarehouses(0, error), false);
  }
  for (const status of [null, 408, 500, 502])
    assert.equal(
      new WarehouseRequestError("Unknown result", status).uncertain,
      true,
    );
  assert.equal(retryWarehouses(0, new Error("network")), true);
  assert.equal(retryWarehouses(1, new Error("network")), false);
});
