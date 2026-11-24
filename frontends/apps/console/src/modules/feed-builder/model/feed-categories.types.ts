import type { SchemaNode, SchemaTransform } from "./feed-schema.types";

export type CategoryPropertyType = "string" | "text" | "integer" | "boolean";
export type CategoryProperty = string | number | boolean;
export type CategoryFallback = "CATALOG" | "FIXED" | "NONE";
export type CategoryPropertyPlacement = "ATTRIBUTE" | "ELEMENT" | "TEXT" | "NONE";

export interface CategoryPropertyDefinition {
  key: string;
  kind: CategoryPropertyType;
  required: boolean;
  xml: { name: string; placement: CategoryPropertyPlacement };
  source: "CATALOG_NAME" | null;
}

export interface FeedCategoryNode {
  id: string;
  parentId: string | null;
  catalogId: string | null;
  inheritParent: boolean;
  values: Record<string, CategoryProperty>;
}

export interface FeedCategoryRule {
  id: string;
  targetId: string;
  label: string;
  condition: SchemaNode;
  includeDescendants: boolean;
}

export interface CategoryType {
  kind: "category";
  locale: string;
  nameTransforms: SchemaTransform[];
  objectSchema: { idKey: string; labelKey: string; fields: CategoryPropertyDefinition[] };
  value: {
    kind: "INLINE";
    nextExportId: number;
    nodes: FeedCategoryNode[];
    rules: FeedCategoryRule[];
    fallback: CategoryFallback;
    fallbackId: string | null;
    catalogPriority: string[];
  };
}

export interface CategoryDocumentExport {
  container: string;
  item: string;
  parent: "ROOT" | "SHOP";
  layout: "FLAT" | "NESTED";
  parentAttribute: string;
}

export interface CategoryPublicationExport {
  valueKey: string;
  required: boolean;
}

export interface PreviewCategory {
  fieldId: string;
  fieldLabel: string;
  nodeId: string;
  exportId: string;
  path: string[];
  ruleLabel: string | null;
}
