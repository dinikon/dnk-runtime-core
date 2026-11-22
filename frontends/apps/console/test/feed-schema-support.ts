import type {
  SchemaMetadata,
  FeedSchemaDefinition,
} from "../src/modules/feed-builder/model/feed-schema.types.ts";
import {
  newSchemaField,
  draftDefinition,
} from "../src/modules/feed-builder/model/feed-schema.draft.ts";
export const schemaMetadata: SchemaMetadata = {
  fieldTypes: [
    {
      kind: "string",
      label: "Короткий текст",
      supportsLocale: true,
      supportsCurrency: false,
      editableModes: ["SOURCE", "MANUAL"],
    },
    {
      kind: "text",
      label: "Длинный текст",
      supportsLocale: true,
      supportsCurrency: false,
      editableModes: ["SOURCE", "MANUAL"],
    },
    {
      kind: "money",
      label: "Денежное значение",
      supportsLocale: false,
      supportsCurrency: true,
      editableModes: ["SOURCE", "MANUAL"],
    },
  ],
  locales: [
    { code: "uk", name: "Українська" },
    { code: "ru", name: "Русский" },
  ],
  maxFields: 200,
  maxTransforms: 128,
  sources: [
    {
      provider: "catalog",
      path: "item.title",
      label: "Название",
      fieldKinds: ["string", "text"],
      requiresLocale: true,
    },
    {
      provider: "catalog",
      path: "item.description",
      label: "Описание",
      fieldKinds: ["string", "text"],
      requiresLocale: true,
    },
    {
      provider: "catalog",
      path: "item.sku",
      label: "SKU",
      fieldKinds: ["string", "text"],
      requiresLocale: false,
    },
    {
      provider: "catalog",
      path: "item.regular_price",
      label: "Цена",
      fieldKinds: ["money"],
      requiresLocale: false,
    },
  ],
  transforms: [
    {
      operation: "string.trim",
      label: "Trim",
      fieldKinds: ["string", "text"],
      parameterKind: "none",
    },
    {
      operation: "string.truncate",
      label: "Truncate",
      fieldKinds: ["string", "text"],
      parameterKind: "max_length",
    },
    {
      operation: "money.ceil_step",
      label: "Ceil",
      fieldKinds: ["money"],
      parameterKind: "step",
    },
  ],
};
export function fourFieldSchema(): FeedSchemaDefinition {
  const fields = (["string", "text", "string", "money"] as const).map(
    (kind, index) =>
      newSchemaField(kind, `00000000-0000-4000-8000-00000000000${index}`, []),
  );
  fields.forEach((field, index) => {
    field.key = ["title", "description", "sku", "price"][index]!;
    field.export.name = field.key;
    field.label = field.key;
    if (field.typeDefinition.kind !== "money") {
      field.typeDefinition.value = {
        kind: "SOURCE",
        source: {
          provider: "catalog",
          path:
            index === 0
              ? "item.title"
              : index === 1
                ? "item.description"
                : "item.sku",
        },
      };
      field.typeDefinition.locale = index === 2 ? null : "uk";
    }
  });
  return draftDefinition({ fields }, schemaMetadata);
}
