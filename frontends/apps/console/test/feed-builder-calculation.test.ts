import { test } from "node:test";
import assert from "node:assert/strict";
import {
  initialCalculation,
  newNode,
  quickExpression,
  moveRule,
  calculationIsSupported,
} from "../src/modules/feed-builder/model/feed-calculation.draft.ts";
import {
  mapPreview,
  previewPayload,
  calculationMetadata,
} from "../src/modules/feed-builder/api/feed-calculation.mapper.ts";
import {
  schemaDraft,
  draftDefinition,
  fieldIsReadonly,
} from "../src/modules/feed-builder/model/feed-schema.draft.ts";
import {
  definitionPayload,
  mapDefinition,
} from "../src/modules/feed-builder/api/feed-schema.mapper.ts";
import { fourFieldSchema, schemaMetadata } from "./feed-schema-support.ts";

import { previewDTO } from "./feed-calculation-support.ts";

test("Calculation AST is editable with current parameters and preserves rules, Decimal constants and optional currency on save/reopen", () => {
  const schema = fourFieldSchema(),
    price = schema.fields[3]!;
  assert.equal(price.typeDefinition.kind, "money");
  if (price.typeDefinition.kind !== "money") throw new Error("fixture");
  const calc = initialCalculation();
  calc.defaultExpression = quickExpression(
    "price.regular",
    "percent",
    "12.1234567890123456789",
  );
  calc.rules = [
    {
      id: "11111111-1111-4111-8111-111111111111",
      condition: newNode("presence"),
      expression: newNode("parameter"),
    },
  ];
  price.typeDefinition.value = {
    kind: "MONEY",
    mode: "CALCULATED",
    calculation: calc,
  };
  const draft = schemaDraft(schema);
  assert.equal(fieldIsReadonly(draft.fields[3]!), false);
  const saved = draftDefinition(draft, schemaMetadata);
  assert.deepEqual(mapDefinition(definitionPayload(saved)), saved);
  assert.equal(JSON.stringify(saved).includes("12.1234567890123456789"), true);
  assert.equal(
    calculationIsSupported({
      ...calc,
      purchaseSource: {
        provider: "supplier_sourcing",
        path: "purchase_price",
        selection: { mode: "SUPPLIER_SOURCE", supplierSourceId: "source" },
      },
    }),
    false,
  );
  assert.equal(
    calculationIsSupported({
      ...calc,
      defaultExpression: {
        kind: "parameter",
        parameter: "product.category_ids",
      },
    }),
    false,
  );
});
test("Rules keep identity while moving; quick actions build AST without floating point evaluation", () => {
  const c = initialCalculation();
  c.rules = ["first", "second"].map((id) => ({
    id,
    condition: newNode("presence"),
    expression: newNode("parameter"),
  }));
  assert.deepEqual(
    moveRule(c, 0, 1).rules.map((r) => r.id),
    ["second", "first"],
  );
  assert.deepEqual(
    c.rules.map((r) => r.id),
    ["first", "second"],
  );
  assert.deepEqual(
    quickExpression("price.sale", "amount", "0.1234567890123456789"),
    {
      kind: "arithmetic",
      operator: "ADD",
      left: { kind: "parameter", parameter: "price.sale" },
      right: { kind: "decimal", value: "0.1234567890123456789" },
    },
  );
});
test("Preview maps source identity, absent/zero/empty inputs and trace without inventing currency", () => {
  const p = mapPreview(previewDTO);
  assert.deepEqual(p.resolvedValue, {
    amount: "1234567890.1234567890123456789",
  });
  assert.equal(p.variantId, "white");
  assert.equal(p.selectedProductId, "white");
  assert.equal(p.sourceRevision, 9);
  assert.deepEqual(
    p.parameters.map((i) => i.value),
    [null, "0", ""],
  );
  assert.equal(p.steps[0]!.ruleId, null);
  const payload = previewPayload({
    feedId: "feed",
    expectedVersion: 7,
    field: fourFieldSchema().fields[3]!,
    itemId: "item",
    variantId: "white",
  });
  assert.equal(payload.catalog_variant_id, "white");
  assert.equal(payload.expected_version, 7);
  assert.ok(payload.definition_override.type_definition);
  assert.equal("prices" in payload, false);
  assert.equal("as_of" in payload, false);
});
test("Metadata maps actual backend budgets and operations into frontend models", () => {
  const metadata = calculationMetadata(
    {
      items: [
        {
          id: "price.sale",
          label: "Акционная",
          value_type: "number",
          nullable: true,
        },
      ],
    },
    {
      items: [
        {
          code: "ADD",
          label: "Сложить",
          category: "arithmetic",
          min_arguments: 2,
          max_arguments: 2,
        },
      ],
      engine_version: "1",
      precision: 40,
      max_depth: 32,
      max_nodes: 4096,
      max_rules: 100,
      max_collection_items: 500,
    },
  );
  assert.equal(metadata.parameters[0]!.valueType, "number");
  assert.equal(metadata.operations[0]!.minArguments, 2);
  assert.equal(metadata.maxRules, 100);
});

test("Oversized unfinished calculation stays editable so the user can remove extra operands", () => {
  const c = initialCalculation();
  c.defaultExpression = {
    kind: "function",
    function: "MAX",
    arguments: Array.from({ length: 4096 }, () => newNode("decimal")),
  };
  assert.equal(calculationIsSupported(c), true);
});
