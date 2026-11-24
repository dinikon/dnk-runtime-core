import type { CategoryType, FeedCategoryNode } from "./feed-categories.types";

export function newCategoryType(locale: string): CategoryType {
  return {
    kind: "category",
    locale,
    nameTransforms: [],
    objectSchema: {
      idKey: "id",
      labelKey: "name",
      fields: [
        { key: "id", kind: "string", required: true, source: null, xml: { placement: "ATTRIBUTE", name: "id" } },
        { key: "name", kind: "text", required: true, source: "CATALOG_NAME", xml: { placement: "TEXT", name: "name" } },
      ],
    },
    value: { kind: "INLINE", nextExportId: 1, nodes: [], rules: [], fallback: "CATALOG", fallbackId: null, catalogPriority: [] },
  };
}

export function newCategory(): FeedCategoryNode {
  return { id: crypto.randomUUID(), parentId: null, catalogId: null, inheritParent: false, values: {} };
}
