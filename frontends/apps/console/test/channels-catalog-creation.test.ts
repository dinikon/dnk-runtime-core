import { test } from "node:test";
import assert from "node:assert/strict";
import { publicationCatalogFromDto } from "../src/modules/channels/api/catalog-creation.mapper.ts";

test("Creation preserves IDs and returns independent warnings for SKU and media", () => {
  const dto = {
    catalog_item_id: "catalog",
    binding_group_id: "binding",
    created: true,
    warnings: ["SKU не перенесён", "Фото пропущено"],
  };
  const result = publicationCatalogFromDto(dto);
  assert.deepEqual(result, {
    catalogItemId: "catalog",
    bindingGroupId: "binding",
    created: true,
    warnings: [...dto.warnings],
  });
  dto.warnings.push("changed");
  assert.equal(result.warnings.length, 2);
});
test("An idempotent response identifies the already linked product", () => {
  const result = publicationCatalogFromDto({
    catalog_item_id: "existing",
    binding_group_id: "binding",
    created: false,
    warnings: [],
  });
  assert.equal(result.created, false);
  assert.equal(result.catalogItemId, "existing");
});
