import { test } from "node:test";
import assert from "node:assert/strict";
import { reactive } from "vue";
import { schemaMetadata, fourFieldSchema } from "./feed-schema-support.ts";
import {
  schemaDraft,
  draftDefinition,
  duplicateSchemaField,
  moveSchemaField,
  validateSchemaDraft,
  acknowledgeSchemaDraft,
  fieldIsReadonly,
} from "../src/modules/feed-builder/model/feed-schema.draft.ts";
import {
  definitionPayload,
  mapDefinition,
  mapFeedSchema,
  saveSchemaPayload,
} from "../src/modules/feed-builder/api/feed-schema.mapper.ts";
import type { SchemaCalculation } from "../src/modules/feed-builder/model/feed-schema.types.ts";

test("Four-field schema maps to exact nested definitions with fixed source paths and no implicit currency", () => {
  const schema = fourFieldSchema(),
    dto = definitionPayload(schema);
  assert.deepEqual(
    dto.root.fields.map((f) => f.type_definition.kind),
    ["string", "text", "string", "money"],
  );
  const price = dto.root.fields[3]!.type_definition;
  assert.equal(price.kind, "money");
  if (price.kind === "money") {
    assert.equal(price.currency, null);
    assert.equal("locale" in price, false);
    assert.equal(price.value.mode, "SOURCE");
  }
  assert.deepEqual(mapDefinition(dto), schema);
  const request = saveSchemaPayload({
    id: "feed",
    expectedVersion: 9,
    definition: schema,
  });
  assert.equal(request.expected_version, 9);
  assert.equal("status" in request, false);
  assert.equal(
    mapFeedSchema({
      feed_id: "feed",
      version: 9,
      status: "ARCHIVED",
      definition: dto,
    }).status,
    "ARCHIVED",
  );
});
test("Vue query proxy inputs produce independent drafts; moves retain IDs and copies get independent settings", () => {
  const original = reactive(fourFieldSchema()),
    draft = schemaDraft(original);
  const copy = duplicateSchemaField(
    draft.fields[0]!,
    "00000000-0000-4000-8000-000000000009",
    draft.fields,
  );
  assert.notEqual(copy.key, draft.fields[0]!.key);
  assert.notEqual(copy.export.name, draft.fields[0]!.export.name);
  copy.label = "Copied";
  copy.export.enabled = false;
  assert.equal(original.fields[0]!.label, "title");
  assert.equal(draft.fields[0]!.export.enabled, true);
  const order = moveSchemaField(draft.fields, draft.fields[3]!.id, -1);
  assert.equal(order[2]!.id, draft.fields[3]!.id);
  assert.equal(draft.fields[3]!.key, "price");
  assert.equal(
    moveSchemaField(draft.fields, draft.fields[0]!.id, -1),
    draft.fields,
  );
});
test("Validation retains incomplete numeric input and rejects duplicates, wrong sources and locale dependencies", () => {
  const draft = schemaDraft(fourFieldSchema()),
    first = draft.fields[0]!,
    price = draft.fields[3]!;
  assert.deepEqual(validateSchemaDraft(draft, schemaMetadata), []);
  draft.fields[1]!.key = first.key;
  assert.ok(
    validateSchemaDraft(draft, schemaMetadata).some(
      (e) => e.path.at(-1) === "key",
    ),
  );
  draft.fields[1]!.key = "description";
  if (first.typeDefinition.kind !== "money") {
    first.typeDefinition.locale = null;
    first.typeDefinition.constraints.minLength = "unfinished";
    assert.equal(first.typeDefinition.constraints.minLength, "unfinished");
    const errors = validateSchemaDraft(draft, schemaMetadata);
    assert.ok(errors.some((e) => e.path.includes("locale")));
    assert.ok(errors.some((e) => e.path.includes("constraints")));
    assert.throws(() => draftDefinition(draft, schemaMetadata));
  }
  if (price.typeDefinition.kind === "money") {
    price.typeDefinition.value = {
      kind: "MONEY",
      mode: "SOURCE",
      source: { provider: "catalog", path: "item.title" },
    };
    price.typeDefinition.currency = "US";
    assert.ok(
      validateSchemaDraft(draft, schemaMetadata).some(
        (e) => e.fieldId === price.id && e.path.includes("source"),
      ),
    );
    assert.ok(
      validateSchemaDraft(draft, schemaMetadata).some((e) =>
        e.path.includes("currency"),
      ),
    );
  }
});
test("Amount boundaries and transform steps stay exact beyond Number precision, including exponent notation", () => {
  const draft = schemaDraft(fourFieldSchema()),
    price = draft.fields[3]!;
  if (price.typeDefinition.kind !== "money") throw new Error("fixture");
  price.typeDefinition.constraints.minAmount =
    "9007199254740993.000000000000001";
  price.typeDefinition.constraints.maxAmount =
    "9007199254740993.000000000000002";
  price.typeDefinition.transforms = [
    { operation: "money.ceil_step", parameter: "1E-18" },
  ];
  price.typeDefinition.currency = "usd";
  assert.deepEqual(validateSchemaDraft(draft, schemaMetadata), []);
  const value = draftDefinition(draft, schemaMetadata),
    roundtrip = mapDefinition(definitionPayload(value));
  assert.deepEqual(roundtrip, value);
  const type = roundtrip.fields[3]!.typeDefinition;
  if (type.kind !== "money") throw new Error("fixture");
  assert.equal(type.currency, "USD");
  assert.equal(type.constraints.minAmount, "9007199254740993.000000000000001");
  price.typeDefinition.constraints.maxAmount =
    "9007199254740993.000000000000000";
  assert.ok(
    validateSchemaDraft(draft, schemaMetadata).some((e) =>
      e.path.includes("constraints"),
    ),
  );
  price.typeDefinition.transforms[0]!.parameter = "NaN";
  assert.ok(
    validateSchemaDraft(draft, schemaMetadata).some((e) =>
      e.path.includes("transforms"),
    ),
  );
});
test("Known calculated fields preserve complete AST, bindings, AI and transform metadata through editor snapshots", () => {
  const schema = fourFieldSchema(),
    price = schema.fields[3]!;
  if (price.typeDefinition.kind !== "money") throw new Error("fixture");
  const calculation: SchemaCalculation = {
    defaultExpression: {
      kind: "arithmetic",
      operator: "DIVIDE",
      left: { kind: "parameter", parameter: "price.regular" },
      right: { kind: "decimal", value: "40.1234567890123456789" },
    },
    rules: [
      {
        id: "00000000-0000-4000-8000-000000000099",
        condition: {
          kind: "logical",
          operator: "ALL",
          operands: [
            {
              kind: "presence",
              operator: "EXISTS",
              parameter: "price.purchase",
            },
            {
              kind: "comparison",
              operator: "IN",
              left: {
                kind: "scalar",
                valueType: "uuid",
                value: "00000000-0000-4000-8000-000000000077",
              },
              right: {
                kind: "collection",
                itemType: "uuid",
                items: [
                  {
                    kind: "scalar",
                    valueType: "uuid",
                    value: "00000000-0000-4000-8000-000000000077",
                  },
                ],
              },
            },
          ],
        },
        expression: {
          kind: "function",
          function: "ABS",
          arguments: [
            {
              kind: "arithmetic",
              operator: "NEGATE",
              operand: { kind: "parameter", parameter: "price.purchase" },
            },
          ],
        },
      },
    ],
    purchaseSource: {
      provider: "supplier_sourcing",
      path: "purchase_price",
      selection: {
        mode: "SUPPLIER_SOURCE",
        supplierSourceId: "00000000-0000-4000-8000-000000000088",
      },
    },
  };
  price.typeDefinition.value = {
    kind: "MONEY",
    mode: "CALCULATED",
    calculation,
  };
  price.aiInstruction = "Retain";
  const draft = schemaDraft(schema);
  assert.equal(fieldIsReadonly(draft.fields[3]!), true);
  draft.fields[0]!.label = "Changed another field";
  const restored = mapDefinition(
    definitionPayload(draftDefinition(draft, schemaMetadata)),
  );
  assert.deepEqual(restored.fields[3], price);
});
test("Acknowledgement replaces only the sent snapshot, retaining later local input and empty schemas", () => {
  const schema = fourFieldSchema(),
    sent = schemaDraft(schema),
    later = schemaDraft(schema);
  later.fields[0]!.label = "Typed during save";
  assert.equal(acknowledgeSchemaDraft(later, sent, schema), later);
  assert.deepEqual(acknowledgeSchemaDraft(sent, sent, schema), sent);
  assert.deepEqual(draftDefinition({ fields: [] }, schemaMetadata), {
    schemaFormatVersion: 1,
    fields: [],
  });
});
