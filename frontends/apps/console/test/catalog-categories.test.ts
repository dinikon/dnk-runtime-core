import { test } from "node:test";
import assert from "node:assert/strict";
import {
  categoryTree,
  choosePrimary,
} from "../src/modules/catalog/model/category-tree.ts";
import type { CatalogCategory } from "../src/modules/catalog/model/category.types.ts";

test("tree displays ancestry and explicitly identifies an untranslated name", () => {
  const node = (
    id: string,
    parentId: string | null,
    name: string | null,
  ): CatalogCategory => ({
    id,
    parentId,
    name,
    sourceName: "Топы",
    sourceLocale: "ru",
    isDefault: false,
  });
  const rows = categoryTree([
    node("child", "parent", null),
    node("parent", null, "Clothing"),
  ]);
  assert.deepEqual(
    rows.map((item) => item.depth),
    [0, 1],
  );
  assert.equal(rows[1]?.path, "Clothing / Топы (ru, нет перевода)");
});
test("promoting a selected category retains the former primary exactly once", () => {
  const selection = {
    primary_category_id: "tops",
    additional_category_ids: ["summer", "sale"],
  };
  assert.deepEqual(choosePrimary(selection, "summer"), {
    primary_category_id: "summer",
    additional_category_ids: ["sale", "tops"],
  });
  assert.deepEqual(selection.additional_category_ids, ["summer", "sale"]);
});
