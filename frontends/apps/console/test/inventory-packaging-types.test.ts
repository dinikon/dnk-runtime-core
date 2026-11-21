import assert from "node:assert/strict";
import test from "node:test";
import { createRenderer, h, effectScope, nextTick, ref } from "vue";
import { createRouter, createMemoryHistory } from "vue-router";
import { usePackagingTypesPageState } from "../src/modules/inventory/model/use-packaging-types-page-state.ts";
import type { InventoryScope } from "../src/modules/inventory/model/inventory-scope.types.ts";
import {
  packagingTypeCreateToDto,
  packagingTypeFromDto,
  packagingTypePatchToDto,
  packagingTypesParamsToDto,
  packagingTypesPageFromDto,
} from "../src/modules/inventory/api/packaging-type.mapper.ts";
import {
  PackagingTypeDraft,
  packagingTypeChanges,
} from "../src/modules/inventory/model/packaging-type-draft.ts";
import { usePackagingTypeDraft } from "../src/modules/inventory/model/use-packaging-type-draft.ts";
import { packagingTypeKeys } from "../src/modules/inventory/model/packaging-type.query-keys.ts";
import {
  parsePackagingTypesParams,
  packagingTypesListParams,
  packagingTypesUrlParams,
} from "../src/modules/inventory/model/packaging-types-page-state.ts";
import {
  packagingTypeEditLocation,
  packagingTypeReturnPath,
} from "../src/modules/inventory/model/packaging-type-navigation.ts";
import { validatePackagingType } from "../src/modules/inventory/model/packaging-type-form.validation.ts";
import {
  PackagingTypeRequestError,
  retryPackagingTypes,
} from "../src/modules/inventory/model/packaging-type.errors.ts";
import type { PackagingTypeEditValues } from "../src/modules/inventory/model/packaging-type.types.ts";
const defaults: PackagingTypeEditValues = {
  code: "main",
  name: "Основной склад",
  isActive: true,
};

test("packaging-type DTO mapping keeps false, creation sends only manual values", () => {
  assert.deepEqual(
    packagingTypeCreateToDto({ code: " Straße ", name: " Name " }),
    {
      code: " Straße ",
      name: " Name ",
    },
  );
  const dto = {
    id: "packaging-type",
    code: "main",
    name: "Основной",
    is_active: false,
  };
  const model = packagingTypeFromDto(dto);
  assert.deepEqual(model, {
    id: "packaging-type",
    code: "main",
    name: "Основной",
    isActive: false,
  });
  assert.deepEqual(
    packagingTypesPageFromDto({
      items: [dto],
      total: 5,
      offset: 20,
      limit: 20,
    }),
    { items: [model], total: 5, offset: 20, limit: 20 },
  );
});

test("partial PATCH sends changed fields including explicit false without readonly attributes", () => {
  const changes = packagingTypeChanges(
    { ...defaults, isActive: false },
    defaults,
  );
  assert.deepEqual(packagingTypePatchToDto(changes), { is_active: false });
  assert.deepEqual(packagingTypePatchToDto({ name: "New" }), { name: "New" });
  assert.deepEqual(
    packagingTypePatchToDto(packagingTypeChanges(defaults, defaults)),
    {},
  );
  assert.deepEqual(
    packagingTypePatchToDto({ code: "A", name: "B", isActive: true }),
    { code: "A", name: "B", is_active: true },
  );
});

test("list params preserve inactive false and literal Unicode search without client casefold", () => {
  assert.deepEqual(
    packagingTypesParamsToDto({
      search: " Straße%_ ",
      offset: 0,
      limit: 50,
      isActive: false,
    }),
    { search: " Straße%_ ", offset: 0, limit: 50, is_active: false },
  );
  assert.deepEqual(
    packagingTypesParamsToDto({
      search: "",
      offset: 0,
      limit: 50,
      isActive: null,
    }),
    { offset: 0, limit: 50 },
  );
});

test("URL page state normalizes invalid values and round trips activity, search and pagination", () => {
  const params = parsePackagingTypesParams({
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
  assert.deepEqual(packagingTypesListParams(params), {
    search: "Київ",
    isActive: false,
    offset: 40,
    limit: 20,
  });
  assert.deepEqual(packagingTypesUrlParams(params), {
    search: "Київ",
    is_active: "false",
    page: "3",
    limit: "20",
  });
  assert.deepEqual(
    parsePackagingTypesParams({
      search: [],
      is_active: "yes",
      page: "NaN",
      limit: "999",
    }),
    { search: "", activity: "all", page: 1, limit: 50 },
  );
  assert.equal(parsePackagingTypesParams({ page: "-5" }).page, 1);
  assert.equal(parsePackagingTypesParams({ page: "2.9" }).page, 2);
  assert.ok(
    Number.isSafeInteger(
      packagingTypesListParams(parsePackagingTypesParams({ page: "1e100" }))
        .offset,
    ),
  );
  assert.equal(
    packagingTypesUrlParams(parsePackagingTypesParams({ is_active: "true" }))
      .is_active,
    "true",
  );
});

test("packaging-type cache keys snapshot filters and isolate tenant, user, session and entity", () => {
  const params = { search: "a", offset: 0, limit: 50, isActive: false };
  const key = packagingTypeKeys.list(["tenant", "user", "1"], params);
  params.offset = 50;
  assert.equal(key[6].offset, 0);
  for (const other of [
    packagingTypeKeys.list(["other", "user", "1"], key[6]),
    packagingTypeKeys.list(["tenant", "other", "1"], key[6]),
    packagingTypeKeys.list(["tenant", "user", "2"], key[6]),
    packagingTypeKeys.list(["tenant", "user", "1"], {
      ...key[6],
      isActive: true,
    }),
    packagingTypeKeys.list(["tenant", "user", "1"], params),
  ])
    assert.notDeepEqual(key, other);
  assert.notDeepEqual(
    packagingTypeKeys.detail(["tenant", "user", "1"], "a"),
    packagingTypeKeys.detail(["tenant", "user", "1"], "b"),
  );
  assert.notDeepEqual(
    packagingTypeKeys.create(["tenant", "user", "1"]),
    packagingTypeKeys.update(["tenant", "user", "1"], "a"),
  );
});

test("draft ignores background refetch and accepts server canonicalization without erasing newer input", () => {
  const draft = new PackagingTypeDraft();
  draft.receive(defaults);
  const sent = { ...defaults, code: " NEW ", isActive: false };
  draft.change(sent);
  draft.receive({ ...defaults, name: "External" });
  assert.deepEqual(draft.values, sent);
  draft.change({ ...sent, name: "Typing while saving", isActive: true });
  draft.acknowledge(sent, { ...sent, code: "NEW" });
  assert.deepEqual(draft.values, {
    code: "NEW",
    name: "Typing while saving",
    isActive: true,
  });
  assert.deepEqual(draft.changes, {
    name: "Typing while saving",
    isActive: true,
  });
  draft.reset({ ...sent, code: "NEW" });
  assert.equal(draft.dirty, false);
  draft.clear();
  assert.equal(draft.values, null);
});

test("successful partial response incorporates independent server changes only for untouched inputs", () => {
  const draft = new PackagingTypeDraft();
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
    source = ref<PackagingTypeEditValues | undefined>(defaults);
  const draft = effects.run(() =>
    usePackagingTypeDraft(() => source.value, identity, pending),
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
    "/inventory/packaging-types?search=a&is_active=false&page=2&limit=20#table";
  assert.equal(packagingTypeReturnPath(path), path);
  assert.deepEqual(packagingTypeEditLocation("id", path), {
    name: "inventory-packaging-type-edit",
    params: { packagingTypeId: "id" },
    query: { returnTo: path },
  });
  for (const value of [
    undefined,
    "https://evil.test",
    "//evil.test",
    "/inventory/packaging-types/other",
    "/inventory/packaging-types\\evil",
    "/inventory/packaging-types\n",
  ])
    assert.equal(packagingTypeReturnPath(value), "/inventory/packaging-types");
});

test("validation assists input while Domain remains responsible for canonical codes", () => {
  assert.deepEqual(
    validatePackagingType({ code: " Straße ", name: " Name " }),
    {},
  );
  assert.deepEqual(
    Object.keys(validatePackagingType({ code: "  ", name: "" })).sort(),
    ["code", "name"],
  );
});

test("write uncertainty never retries automatically; reads do not retry client rejections", () => {
  for (const status of [403, 404, 409, 422]) {
    const error = new PackagingTypeRequestError("Rejected", status);
    assert.equal(error.uncertain, false);
    assert.equal(retryPackagingTypes(0, error), false);
  }
  for (const status of [null, 408, 500, 502])
    assert.equal(
      new PackagingTypeRequestError("Unknown result", status).uncertain,
      true,
    );
  assert.equal(retryPackagingTypes(0, new Error("network")), true);
  assert.equal(retryPackagingTypes(1, new Error("network")), false);
});

test("codes keep exact case in creation and changes, and update keys include the entity", () => {
  assert.deepEqual(packagingTypeCreateToDto({ code: " BOX ", name: "Box" }), {
    code: " BOX ",
    name: "Box",
  });
  assert.deepEqual(
    packagingTypePatchToDto(
      packagingTypeChanges(
        { ...defaults, code: "box" },
        { ...defaults, code: "BOX" },
      ),
    ),
    { code: "box" },
  );
  assert.notDeepEqual(
    packagingTypeKeys.update(["tenant", "user", "1"], "a"),
    packagingTypeKeys.update(["tenant", "user", "1"], "b"),
  );
  assert.ok(
    packagingTypesListParams(parsePackagingTypesParams({ page: "1e100" }))
      .offset <= 2147483647,
  );
});

test("list URL preserves unrelated parameters, applies pending search with filters and disposes timers", async () => {
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
  const scope = ref<InventoryScope>(["tenant", "user", "1"]);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/:pathMatch(.*)*", component: { render: () => null } }],
  });
  await router.push(
    "/inventory/packaging-types?custom=keep&is_active=false&page=3#table",
  );
  let state!: ReturnType<typeof usePackagingTypesPageState>;
  const app = renderer.createApp({
    setup() {
      state = usePackagingTypesPageState(scope);
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
    state.setActivity("active");
    await flush();
    assert.equal(state.params.value.page, 1);
    assert.equal(state.params.value.search, "BOX");
    assert.equal(state.listParams.value.isActive, true);
    assert.equal(router.currentRoute.value.query.custom, "keep");
    assert.equal(router.currentRoute.value.hash, "#table");
    state.setPagination({ page: 2, limit: 20 });
    await flush();
    assert.equal(state.params.value.page, 1);
    state.setPagination({ page: 2, limit: 20 });
    await flush();
    assert.equal(state.listParams.value.offset, 20);
    state.searchAll("box");
    await flush();
    assert.equal(state.params.value.activity, "all");
    assert.equal(state.params.value.search, "box");
    assert.equal(state.params.value.page, 1);
    state.setSearch("late context");
    scope.value = ["tenant-b", "user", "2"];
    await flush();
    assert.equal(state.searchText.value, "");
    assert.equal(state.params.value.search, "");
    assert.equal(state.params.value.activity, "all");
    state.setSearch("disposed");
    app.unmount();
    mounted = false;
    await new Promise((resolve) => setTimeout(resolve, 350));
    assert.equal(router.currentRoute.value.query.search, undefined);
  } finally {
    if (mounted) app.unmount();
  }
});
