import type { SchemaField, SchemaNode } from "./feed-schema.types.ts";
export interface CalculationParameter {
  id: string;
  label: string;
  valueType: string;
  nullable: boolean;
}
export interface CalculationOperation {
  code: string;
  category: string;
  label: string;
  minArguments: number;
  maxArguments: number;
}
export interface CalculationMetadata {
  parameters: CalculationParameter[];
  operations: CalculationOperation[];
  engineVersion: string;
  precision: number;
  maxDepth: number;
  maxNodes: number;
  maxRules: number;
  maxCollectionItems: number;
}
export interface PreviewRequest {
  feedId: string;
  expectedVersion: number;
  field: SchemaField;
  itemId: string;
  variantId: string | null;
}
export type TraceValue = string | boolean | (string | boolean)[] | null;
export interface CalculationPreview {
  feedId: string;
  version: number;
  fieldId: string;
  definitionHash: string;
  itemId: string;
  variantId: string | null;
  selectedProductId: string;
  productKind: string;
  sku: string | null;
  sourceRevision: number;
  asOf: string;
  validUntil: string | null;
  engineVersion: string;
  validationStatus: "VALID" | "INVALID";
  resolvedValue: { amount: string; currency?: string } | null;
  selectedRuleId: string | null;
  usedDefault: boolean;
  steps: {
    path: (string | number)[];
    operation: string;
    value: TraceValue;
    ruleId: string | null;
  }[];
  parameters: { id: string; value: TraceValue }[];
  issues: {
    code: string;
    message: string;
    fieldId: string;
    ruleId: string | null;
    path: (string | number)[];
  }[];
}
export interface CatalogPriceChoice {
  id: string;
  title: string;
  sku: string | null;
  kind: "simple" | "variable" | "variant";
}
export type NodeCategory = "number" | "condition" | "value";
export type NodeKind = SchemaNode["kind"];

export interface CatalogPricePage {
  items: CatalogPriceChoice[];
  total: number;
}
