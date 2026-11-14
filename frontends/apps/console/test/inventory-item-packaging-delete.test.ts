import assert from "node:assert/strict";
import test from "node:test";
import { QueryClient } from "@tanstack/vue-query";
import { itemPackagingKeys } from "../src/modules/inventory/model/item-packaging.query-keys.ts";
import {
  withoutItemPackaging,
  forgetItemPackaging,
  discardItemPackagingContext,
} from "../src/modules/inventory/model/item-packaging-removal.ts";
import type { InventoryScope } from "../src/modules/inventory/model/inventory-scope.types.ts";
import type { ItemPackagingsPage } from "../src/modules/inventory/model/item-packaging.types.ts";
const scope: InventoryScope = ["tenant", "user", "1"];
const item = {
  id: "a",
  inventoryItemId: "sku",
  packagingTypeId: "inactive",
  code: "BOX",
  name: "Ящик",
  contentQuantity: "1.234567890123456789",
  contentUom: "KG",
};
const page: ItemPackagingsPage = {
  items: [item, { ...item, id: "b" }],
  total: 51,
  offset: 0,
  limit: 50,
};
const input = () => ({
  scope,
  itemId: "sku",
  id: "a",
  signal: new AbortController().signal,
});
test("confirmed removal changes only pages containing the ID and is idempotent", () => {
  const result = withoutItemPackaging(page, "a")!;
  assert.deepEqual(
    result.items.map((row) => row.id),
    ["b"],
  );
  assert.equal(result.total, 50);
  assert.equal(result.items[0]?.contentQuantity, item.contentQuantity);
  assert.equal(withoutItemPackaging(result, "a"), result);
  assert.equal(withoutItemPackaging(page, "absent"), page);
  assert.equal(withoutItemPackaging(undefined, "a"), undefined);
  assert.equal(page.items.length, 2);
});
test("cache removal isolates owner, tenant, user, session, detail and list namespaces", async () => {
  const cache = new QueryClient();
  try {
    const list = itemPackagingKeys.list(scope, "sku", {
      search: "BOX",
      offset: 0,
      limit: 50,
    });
    const otherPage = itemPackagingKeys.list(scope, "sku", {
      search: "",
      offset: 50,
      limit: 50,
    });
    const untouched = [
      itemPackagingKeys.list(scope, "other", list[7]),
      itemPackagingKeys.list(["other", "user", "1"], "sku", list[7]),
      itemPackagingKeys.list(["tenant", "other", "1"], "sku", list[7]),
      itemPackagingKeys.list(["tenant", "user", "2"], "sku", list[7]),
      ["inventory", ...scope, "packaging-types", "list"],
      ["catalog", ...scope, "list"],
    ];
    cache.setQueryData(list, page);
    cache.setQueryData(otherPage, { ...page, items: [{ ...item, id: "c" }] });
    cache.setQueryData(itemPackagingKeys.detail(scope, "sku", "a"), item);
    cache.setQueryData(itemPackagingKeys.detail(scope, "sku", "b"), {
      ...item,
      id: "b",
    });
    for (const key of untouched) cache.setQueryData(key, page);
    await forgetItemPackaging(cache, input(), () => true);
    assert.equal(
      cache.getQueryData(itemPackagingKeys.detail(scope, "sku", "a")),
      undefined,
    );
    assert.ok(cache.getQueryData(itemPackagingKeys.detail(scope, "sku", "b")));
    assert.equal(cache.getQueryData<ItemPackagingsPage>(list)?.total, 50);
    assert.equal(cache.getQueryData<ItemPackagingsPage>(otherPage)?.total, 51);
    assert.equal(cache.getQueryState(list)?.isInvalidated, true);
    assert.equal(cache.getQueryState(otherPage)?.isInvalidated, true);
    for (const key of untouched) {
      assert.deepEqual(cache.getQueryData(key), page);
      assert.equal(cache.getQueryState(key)?.isInvalidated, false);
    }
    await forgetItemPackaging(cache, input(), () => true);
    assert.equal(cache.getQueryData<ItemPackagingsPage>(list)?.total, 50);
  } finally {
    cache.clear();
  }
});
test("late list/detail reads cannot resurrect a confirmed deletion", async () => {
  const cache = new QueryClient();
  let releaseList!: (value: ItemPackagingsPage) => void,
    releaseDetail!: (value: typeof item) => void;
  const list = itemPackagingKeys.list(scope, "sku", {
    search: "",
    offset: 0,
    limit: 50,
  });
  const detail = itemPackagingKeys.detail(scope, "sku", "a");
  let aborted = 0;
  try {
    cache.setQueryData(list, page);
    cache.setQueryData(detail, item);
    const readList = cache
      .fetchQuery({
        queryKey: list,
        queryFn: ({ signal }) => {
          signal.addEventListener("abort", () => aborted++);
          return new Promise<ItemPackagingsPage>(
            (resolve) => (releaseList = resolve),
          );
        },
      })
      .catch(() => undefined);
    const readDetail = cache
      .fetchQuery({
        queryKey: detail,
        queryFn: ({ signal }) => {
          signal.addEventListener("abort", () => aborted++);
          return new Promise<typeof item>(
            (resolve) => (releaseDetail = resolve),
          );
        },
      })
      .catch(() => undefined);
    await forgetItemPackaging(cache, input(), () => true);
    releaseList(page);
    releaseDetail(item);
    await Promise.all([readList, readDetail]);
    assert.equal(aborted, 2);
    assert.equal(cache.getQueryData(detail), undefined);
    assert.deepEqual(
      cache.getQueryData<ItemPackagingsPage>(list)?.items.map((row) => row.id),
      ["b"],
    );
  } finally {
    cache.clear();
  }
});
test("context changes before or during cancellation prevent cache writes", async () => {
  const cache = new QueryClient(),
    key = itemPackagingKeys.list(scope, "sku", {
      search: "",
      offset: 0,
      limit: 50,
    });
  try {
    cache.setQueryData(key, page);
    await forgetItemPackaging(cache, input(), () => false);
    assert.deepEqual(cache.getQueryData(key), page);
    let checks = 0;
    await forgetItemPackaging(cache, input(), () => ++checks === 1);
    assert.deepEqual(cache.getQueryData(key), page);
    assert.equal(cache.getQueryState(key)?.isInvalidated, false);
  } finally {
    cache.clear();
  }
});
test("delete keys identify the complete session, owner and selected target", () => {
  const key = itemPackagingKeys.delete(scope, "sku", "a");
  for (const other of [
    itemPackagingKeys.delete(scope, "other", "a"),
    itemPackagingKeys.delete(scope, "sku", "b"),
    itemPackagingKeys.delete(["tenant", "user", "2"], "sku", "a"),
    itemPackagingKeys.update(scope, "sku", "a"),
  ])
    assert.notDeepEqual(key, other);
});

test("inaccessible owner cache is cancelled and discarded without touching another owner", async () => {
  const cache = new QueryClient();
  const key = itemPackagingKeys.list(scope, "sku", {
    search: "",
    offset: 0,
    limit: 50,
  });
  const other = itemPackagingKeys.list(scope, "other", key[7]);
  try {
    cache.setQueryData(key, page);
    cache.setQueryData(other, page);
    await discardItemPackagingContext(cache, input(), () => false);
    assert.ok(cache.getQueryData(key));
    await discardItemPackagingContext(cache, input(), () => true);
    assert.equal(cache.getQueryData(key), undefined);
    assert.deepEqual(cache.getQueryData(other), page);
  } finally {
    cache.clear();
  }
});
