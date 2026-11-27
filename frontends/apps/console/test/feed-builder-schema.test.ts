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
  newSchemaField,
} from "../src/modules/feed-builder/model/feed-schema.draft.ts";
import {
  definitionPayload,
  mapDefinition,
  mapFeedSchema,
  saveSchemaPayload,
} from "../src/modules/feed-builder/api/feed-schema.mapper.ts";
import type { SchemaCalculation, SchemaNode } from "../src/modules/feed-builder/model/feed-schema.types.ts";
import type { FeedCategoryRule } from "../src/modules/feed-builder/model/feed-categories.types.ts";

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
test("Two category fields keep independent object schemas and output bindings", () => {
  const draft = schemaDraft(fourFieldSchema());
  const first = newSchemaField("category", "00000000-0000-4000-8000-000000000012", draft.fields, "ru");
  draft.fields.push(first);
  const second = newSchemaField("category", "00000000-0000-4000-8000-000000000013", draft.fields, "ru");
  draft.fields.push(second);
  if (first.typeDefinition.kind !== "category" || second.typeDefinition.kind !== "category") throw new Error("fixture");
  first.export.document = { container: "categories", item: "category", parent: "ROOT", layout: "FLAT", parentAttribute: "parentId" };
  first.typeDefinition.objectSchema.fields.push({
    key: "prom_id", kind: "string", required: false, source: null,
    xml: { name: "portal_id", placement: "ATTRIBUTE" },
  });
  const id = "00000000-0000-4000-8000-000000000014";
  first.typeDefinition.value.nodes.push({ id, values: { id: "20", name: "Биодобавки", prom_id: "12345" }, parentId: null, catalogId: null, inheritParent: false });
  second.typeDefinition.value.nodes.push({ id, values: { id: "20", name: "Склад" }, parentId: null, catalogId: null, inheritParent: false });
  const payload = definitionPayload(draftDefinition(draft, schemaMetadata));
  assert.equal("categories" in payload, false);
  assert.equal(payload.root.fields.at(-2)?.export.document?.container, "categories");
  assert.equal(payload.root.fields.at(-1)?.export.document, undefined);
  assert.deepEqual(schemaDraft(mapDefinition(payload)), draft);
});

test("The flat graph writes a shared category tree once and keeps Offer references by ID", () => {
  const draft = schemaDraft(fourFieldSchema());
  const treeId = "00000000-0000-4000-8000-000000000017";
  const first = newSchemaField("category", "00000000-0000-4000-8000-000000000012", draft.fields);
  draft.fields.push({ ...first, categoryTreeId: treeId });
  const second = newSchemaField("category", "00000000-0000-4000-8000-000000000013", draft.fields);
  draft.fields.push({ ...second, categoryTreeId: treeId });
  const payload = definitionPayload({ ...draftDefinition(draft, schemaMetadata), schemaFormatVersion: 2 });
  assert.equal(payload.schema_format_version, 2);
  assert.equal("root" in payload, false);
  assert.deepEqual(payload.categoryTrees?.map((tree) => tree.id), [treeId]);
  assert.deepEqual(
    payload.fields.slice(-2).map((node) => ({ id: node.id, typeId: node.typeId, data: node.data })),
    [first, second].map((field) => ({
      id: field.id, typeId: "core.category_reference", data: { source: "feed", treeId },
    })),
  );
  const reloaded = mapDefinition(payload);
  assert.equal(reloaded.fields.at(-1)?.categoryTreeId, treeId);
  assert.deepEqual(definitionPayload(reloaded), payload);
});

test("Category membership validation identifies a nested operand and accepts a Catalog UUID", () => {
  const field = newSchemaField("category", "00000000-0000-4000-8000-000000000012", []);
  if (field.typeDefinition.kind !== "category") throw new Error("fixture");
  const membership: Extract<SchemaNode, { kind: "comparison" }> = {
    kind: "comparison",
    operator: "CONTAINS",
    left: { kind: "parameter", parameter: "product.category_ids" },
    right: { kind: "scalar", valueType: "boolean", value: true },
  };
  const rule: FeedCategoryRule = {
    id: "rule",
    targetId: "local-category",
    label: "По Catalog",
    includeDescendants: false,
    condition: {
      kind: "logical",
      operator: "ALL",
      operands: [membership],
    },
  };
  field.typeDefinition.value.rules.push(rule);
  const draft = { fields: [field] };
  const [error] = validateSchemaDraft(draft, schemaMetadata);
  assert.equal(error?.fieldId, field.id);
  assert.deepEqual(error?.path.slice(-6), ["rules", 0, "condition", "operands", 0, "right"]);
  membership.right = { kind: "scalar", valueType: "uuid", value: "00000000-0000-4000-8000-000000000077" };
  assert.deepEqual(validateSchemaDraft(draft, schemaMetadata), []);
});

test("Rich text fields keep the HTML source and locale chain through V2", () => {
  const field = newSchemaField("rich_text", "00000000-0000-4000-8000-000000000016", [], "uk");
  if (field.typeDefinition.kind !== "rich_text") throw new Error("fixture");
  field.typeDefinition.fallbackPolicy = { mode: "LOCALE_CHAIN", locales: ["ru"] };
  const metadata: typeof schemaMetadata = {
    ...schemaMetadata,
    sources: [...schemaMetadata.sources, {
      provider: "catalog", path: "item.description_html", label: "Описание (HTML)",
      fieldKinds: ["rich_text"], requiresLocale: true,
    }],
  };
  const draft = { fields: [field] };
  assert.deepEqual(validateSchemaDraft(draft, metadata), []);
  const payload = definitionPayload({ ...draftDefinition(draft, metadata), schemaFormatVersion: 2 });
  assert.equal(payload.schema_format_version, 2);
  assert.equal(payload.fields[0]?.typeId, "core.rich_text");
  assert.deepEqual(payload.fields[0]?.data, {
    locale: "uk", fallback_policy: { mode: "LOCALE_CHAIN", locales: ["ru"] },
    value: { kind: "SOURCE", source: { provider: "catalog", path: "item.description_html" } },
    constraints: { required: false, min_length: null, max_length: null }, transforms: [],
  });
  assert.deepEqual(schemaDraft(mapDefinition(payload)).fields, draft.fields);
});

test("Static text in short and multiline fields round-trips through the schema API", () => {
  const draft = schemaDraft(fourFieldSchema());
  const texts = [" r ", "Первая строка\nВторая строка"];
  for (const [index, value] of texts.entries()) {
    const type = draft.fields[index]!.typeDefinition;
    if (type.kind !== "string" && type.kind !== "text") throw new Error("fixture");
    type.locale = null;
    type.value = { kind: "CONSTANT", value };
  }
  const payload = definitionPayload(draftDefinition(draft, schemaMetadata));
  assert.deepEqual(
    payload.root.fields.slice(0, 2).map((field) => field.type_definition.value),
    texts.map((value) => ({ kind: "CONSTANT", value })),
  );
  assert.deepEqual(schemaDraft(mapDefinition(payload)), draft);
});
test("XML placement survives API mapping and returning to element restores the default", () => {
  const draft = schemaDraft(fourFieldSchema());
  const field = draft.fields[0]!;
  assert.equal(field.export.xmlPlacement, "ELEMENT");
  field.export.xmlPlacement = "ATTRIBUTE";
  const payload = definitionPayload(draftDefinition(draft, schemaMetadata));
  assert.equal(payload.root.fields[0]!.export.xml_placement, "ATTRIBUTE");
  const reloaded = schemaDraft(mapDefinition(payload));
  assert.equal(reloaded.fields[0]!.export.xmlPlacement, "ATTRIBUTE");

  field.export.name = "xmlns";
  assert.ok(validateSchemaDraft(draft, schemaMetadata).some((error) =>
    error.fieldId === field.id && error.path.at(-1) === "name"
  ));
  field.export.xmlPlacement = "ELEMENT";
  const reset = definitionPayload(draftDefinition(draft, schemaMetadata));
  assert.equal(reset.root.fields[0]!.export.xml_placement, undefined);
});
test("Integer zero and false IF/ELSE values round-trip through the draft and API", () => {
  const integer = newSchemaField("integer", "00000000-0000-4000-8000-000000000001", []);
  const boolean = newSchemaField("boolean", "00000000-0000-4000-8000-000000000002", [integer]);
  const quantity = integer.typeDefinition;
  const availability = boolean.typeDefinition;
  if (quantity.kind !== "integer" || availability.kind !== "boolean") throw new Error("fixture");

  const condition = {
    kind: "logical",
    operator: "ALL",
    operands: [
      { kind: "presence", operator: "EXISTS", parameter: "stock.quantity" },
      {
        kind: "comparison",
        operator: "LT",
        left: { kind: "parameter", parameter: "stock.quantity" },
        right: { kind: "decimal", value: "2" },
      },
    ],
  } as const;
  quantity.value = { kind: "CONSTANT", value: "0" };
  quantity.constraints.minValue = "0";
  availability.value = {
    kind: "CALCULATED",
    condition: { ...condition, operands: [...condition.operands] },
    thenValue: true,
    elseValue: false,
  };
  const draft = { fields: [integer, boolean] };
  const payload = definitionPayload(draftDefinition(draft, schemaMetadata));
  assert.deepEqual(payload.root.fields[0]!.type_definition.value, { kind: "CONSTANT", value: 0 });
  assert.deepEqual(payload.root.fields[1]!.type_definition.value, {
    kind: "CALCULATED",
    condition,
    then_value: true,
    else_value: false,
  });
  assert.deepEqual(schemaDraft(mapDefinition(payload)), draft);

  quantity.value.value = "-1";
  assert.ok(validateSchemaDraft(draft, schemaMetadata).some((error) => error.fieldId === integer.id));
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
