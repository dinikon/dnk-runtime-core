import type { CategoryType, CategoryDocumentExport, CategoryPublicationExport } from "./feed-categories.types";
import type { FeedStatus } from "./feed.types.ts";
export type FieldKind = "string" | "text" | "rich_text" | "money" | "integer" | "boolean" | "category";
export type XmlFieldPlacement = "ELEMENT" | "ATTRIBUTE";
export type SourcePath =
  | "item.title" | "item.description" | "item.description_html" | "item.sku" | "item.regular_price"
  | "item.stock_quantity" | "item.in_stock";
export interface SchemaSource {
  provider: "catalog";
  path: SourcePath;
}
export type SchemaNode =
  | { kind: "parameter"; parameter: string }
  | { kind: "decimal"; value: string }
  | {
      kind: "scalar";
      valueType: "uuid" | "string" | "boolean";
      value: string | boolean;
    }
  | {
      kind: "collection";
      itemType: "uuid" | "string" | "boolean";
      items: SchemaNode[];
    }
  | {
      kind: "arithmetic";
      operator: "ADD" | "SUBTRACT" | "MULTIPLY" | "DIVIDE" | "NEGATE";
      left?: SchemaNode;
      right?: SchemaNode;
      operand?: SchemaNode;
    }
  | {
      kind: "function";
      function: "MIN" | "MAX" | "ABS";
      arguments: SchemaNode[];
    }
  | {
      kind: "comparison";
      operator:
        | "EQ"
        | "NE"
        | "GT"
        | "GTE"
        | "LT"
        | "LTE"
        | "IN"
        | "NOT_IN"
        | "CONTAINS";
      left: SchemaNode;
      right: SchemaNode;
    }
  | { kind: "logical"; operator: "ALL" | "ANY" | "NOT"; operands: SchemaNode[] }
  | { kind: "presence"; operator: "EXISTS" | "IS_MISSING"; parameter: string };
export interface SchemaCalculation {
  defaultExpression: SchemaNode;
  rules: { id: string; condition: SchemaNode; expression: SchemaNode }[];
  purchaseSource: {
    provider: "supplier_sourcing";
    path: "purchase_price";
    selection: { mode: "SUPPLIER_SOURCE"; supplierSourceId: string };
  } | null;
}
export type SchemaTransform =
  | { operation: "string.trim"; parameters: Record<string, never> }
  | { operation: "string.truncate"; parameters: { maxLength: number } }
  | { operation: "money.ceil_step"; parameters: { step: string } };
type DirectValue =
  | { kind: "SOURCE"; source: SchemaSource }
  | { kind: "MANUAL" };
export type TextValue = DirectValue | { kind: "CONSTANT"; value: string };
export type MoneyValue =
  | { kind: "MONEY"; mode: "SOURCE"; source: SchemaSource }
  | { kind: "MONEY"; mode: "MANUAL" }
  | { kind: "MONEY"; mode: "CALCULATED"; calculation: SchemaCalculation };
export type FallbackMode = "NONE" | "LOCALE_CHAIN" | "MANUAL_REQUIRED";
export interface TextType {
  kind: "string" | "text" | "rich_text";
  locale: string | null;
  fallbackPolicy: { mode: FallbackMode; locales: string[] } | null;
  constraints: {
    required: boolean;
    minLength: number | null;
    maxLength: number | null;
  };
  value: TextValue;
  transforms: SchemaTransform[];
}
export interface MoneyType {
  kind: "money";
  currency: string | null;
  constraints: {
    required: boolean;
    minAmount: string | null;
    maxAmount: string | null;
  };
  value: MoneyValue;
  transforms: SchemaTransform[];
}
export interface BooleanCalculation {
  kind: "CALCULATED";
  condition: SchemaNode;
  thenValue: boolean;
  elseValue: boolean;
}
export interface IntegerType {
  kind: "integer";
  value: DirectValue | { kind: "CONSTANT"; value: number };
  constraints: { required: boolean; minValue: number | null; maxValue: number | null };
}
export interface BooleanType {
  kind: "boolean";
  value: DirectValue | { kind: "CONSTANT"; value: boolean } | BooleanCalculation;
  constraints: { required: boolean };
}
export interface SchemaField {
  id: string;
  key: string;
  label: string;
  typeDefinition: TextType | MoneyType | IntegerType | BooleanType | CategoryType;
  export: { name: string; enabled: boolean; xmlPlacement: XmlFieldPlacement; document?: CategoryDocumentExport; publication?: CategoryPublicationExport };
  aiInstruction: string | null;
  categoryTreeId?: string;
}
export interface FeedCategoryTree {
  id: string;
  settings: CategoryType;
}
export interface FeedSchemaDefinition {
  schemaFormatVersion: 1 | 2;
  fields: SchemaField[];
  categoryTrees?: FeedCategoryTree[];
}
export interface FeedSchema {
  feedId: string;
  version: number;
  status: FeedStatus;
  definition: FeedSchemaDefinition;
}
export interface SavedFeedSchema {
  feedId: string;
  version: number;
  definition: FeedSchemaDefinition;
}
export interface SaveFeedSchema {
  id: string;
  expectedVersion: number;
  definition: FeedSchemaDefinition;
}
export interface NodeFormControl {
  kind: "input" | "textarea" | "rich_text" | "select" | "number" | "decimal" | "checkbox" |
    "conditions" | "categories" | "transforms";
  path: string;
  label: string;
  options?: string[];
  optionsSource?: string;
  visibleInModes?: string[];
  maxLength?: number;
}
export interface NodeForms {
  settings: NodeFormControl[];
  publicationOverride: NodeFormControl[];
}
export interface SchemaMetadata {
  fieldTypes: {
    kind: FieldKind;
    label: string;
    supportsLocale: boolean;
    supportsCurrency: boolean;
    editableModes: string[];
    typeId?: string;
    typeVersion?: number;
    forms?: NodeForms;
  }[];
  locales: { code: string; name: string }[];
  maxFields: number;
  maxTransforms: number;
  sources: {
    provider: "catalog";
    path: SourcePath;
    label: string;
    fieldKinds: FieldKind[];
    requiresLocale: boolean;
  }[];
  transforms: {
    operation: SchemaTransform["operation"];
    label: string;
    fieldKinds: FieldKind[];
    parameterKind: "none" | "max_length" | "step";
  }[];
}
export { FeedRequestError as SchemaApiError, type FeedRequestIssue as SchemaIssue } from "./feed-request-error.ts";
export type DraftTransform = {
  operation: SchemaTransform["operation"];
  parameter: string;
};
export type TextTypeDraft = Omit<
  TextType,
  "constraints" | "transforms" | "value"
> & {
  constraints: { required: boolean; minLength: string; maxLength: string };
  transforms: DraftTransform[];
  value:
    | { kind: "SOURCE"; source: { provider: "catalog"; path: SourcePath | "" } }
    | Exclude<TextValue, { kind: "SOURCE" }>;
};
export type MoneyTypeDraft = Omit<
  MoneyType,
  "constraints" | "transforms" | "value"
> & {
  constraints: { required: boolean; minAmount: string; maxAmount: string };
  transforms: DraftTransform[];
  value:
    | {
        kind: "MONEY";
        mode: "SOURCE";
        source: { provider: "catalog"; path: SourcePath | "" };
      }
    | Exclude<MoneyValue, { mode: "SOURCE" }>;
};
export interface IntegerTypeDraft {
  kind: "integer";
  value: DirectValue | { kind: "CONSTANT"; value: string };
  constraints: { required: boolean; minValue: string; maxValue: string };
}
export type ScalarTypeDraft = IntegerTypeDraft | BooleanType;
export type SchemaFieldDraft = Omit<SchemaField, "typeDefinition"> & {
  typeDefinition: TextTypeDraft | MoneyTypeDraft | ScalarTypeDraft | CategoryType;
};
export interface FeedSchemaDraft {
  fields: SchemaFieldDraft[];
  categoryTrees?: FeedCategoryTree[];
}
