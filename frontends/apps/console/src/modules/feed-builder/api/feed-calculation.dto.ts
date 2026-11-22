import type { SchemaFieldDTO } from "./feed-schema.dto.ts";
export interface CalculationParametersDTO {
  items: { id: string; label: string; value_type: string; nullable: boolean }[];
}
export interface CalculationOperationsDTO {
  items: {
    code: string;
    category: string;
    label: string;
    min_arguments: number;
    max_arguments: number;
  }[];
  engine_version: string;
  precision: number;
  max_depth: number;
  max_nodes: number;
  max_rules: number;
  max_collection_items: number;
}
export interface PreviewRequestDTO {
  expected_version: number;
  field_id: string;
  catalog_item_id: string;
  catalog_variant_id: string | null;
  definition_override: SchemaFieldDTO;
}
export type TraceValueDTO = string | boolean | (string | boolean)[] | null;
export interface CalculationPreviewDTO {
  feed_id: string;
  version: number;
  field_id: string;
  definition_hash: string;
  catalog_item_id: string;
  catalog_variant_id: string | null;
  selected_product_id: string;
  product_kind: string;
  sku: string | null;
  source_revision: number;
  as_of: string;
  valid_until: string | null;
  calculation_engine_version: string;
  validation_status: "VALID" | "INVALID";
  resolved_value: { amount: string; currency?: string } | null;
  selected_rule_id: string | null;
  used_default: boolean;
  steps: {
    path: (string | number)[];
    operation: string;
    value: TraceValueDTO;
    rule_id: string | null;
  }[];
  parameters: { id: string; value: TraceValueDTO }[];
  issues: {
    code: string;
    message: string;
    field_id: string;
    rule_id: string | null;
    path: (string | number)[];
  }[];
}
