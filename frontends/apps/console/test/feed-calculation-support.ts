import type { CalculationPreviewDTO } from "../src/modules/feed-builder/api/feed-calculation.dto.ts";
export const previewDTO: CalculationPreviewDTO = {
  feed_id: "feed",
  version: 7,
  field_id: "price",
  definition_hash: "hash",
  catalog_item_id: "item",
  catalog_variant_id: "white",
  selected_product_id: "white",
  product_kind: "variant",
  sku: "WHITE",
  source_revision: 9,
  as_of: "2026-11-22T12:00:00Z",
  valid_until: null,
  calculation_engine_version: "1",
  validation_status: "VALID",
  resolved_value: { amount: "1234567890.1234567890123456789" },
  selected_rule_id: null,
  used_default: true,
  steps: [
    {
      path: ["default_expression"],
      operation: "price.regular",
      value: "0",
      rule_id: null,
    },
  ],
  parameters: [
    { id: "price.sale", value: null },
    { id: "price.regular", value: "0" },
    { id: "product.sku", value: "" },
  ],
  issues: [],
};
