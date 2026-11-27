import type {
  CalculationParametersDTO,
  CalculationOperationsDTO,
  CalculationPreviewDTO,
  PreviewRequestDTO,
} from "./feed-calculation.dto.ts";
import type {
  CalculationMetadata,
  CalculationPreview,
  PreviewRequest,
} from "../model/feed-calculation.types.ts";
import { graphFieldPayload } from "./feed-schema.mapper.ts";
export function calculationMetadata(
  parameters: CalculationParametersDTO,
  operations: CalculationOperationsDTO,
): CalculationMetadata {
  return {
    parameters: parameters.items.map((p) => ({
      id: p.id,
      label: p.label,
      valueType: p.value_type,
      nullable: p.nullable,
    })),
    operations: operations.items.map((o) => ({
      code: o.code,
      label: o.label,
      category: o.category,
      minArguments: o.min_arguments,
      maxArguments: o.max_arguments,
    })),
    engineVersion: operations.engine_version,
    precision: operations.precision,
    maxDepth: operations.max_depth,
    maxNodes: operations.max_nodes,
    maxRules: operations.max_rules,
    maxCollectionItems: operations.max_collection_items,
  };
}
export function previewPayload(request: PreviewRequest): PreviewRequestDTO {
  return {
    expected_version: request.expectedVersion,
    field_id: request.field.id,
    catalog_item_id: request.itemId,
    catalog_variant_id: request.variantId,
    definition_override: graphFieldPayload(request.field),
  };
}
export function mapPreview(d: CalculationPreviewDTO): CalculationPreview {
  return {
    feedId: d.feed_id,
    version: d.version,
    fieldId: d.field_id,
    definitionHash: d.definition_hash,
    itemId: d.catalog_item_id,
    variantId: d.catalog_variant_id,
    selectedProductId: d.selected_product_id,
    productKind: d.product_kind,
    sku: d.sku,
    sourceRevision: d.source_revision,
    asOf: d.as_of,
    validUntil: d.valid_until,
    engineVersion: d.calculation_engine_version,
    validationStatus: d.validation_status,
    resolvedValue: d.resolved_value,
    selectedRuleId: d.selected_rule_id,
    usedDefault: d.used_default,
    steps: d.steps.map((s) => ({
      path: s.path,
      operation: s.operation,
      value: s.value,
      ruleId: s.rule_id,
    })),
    parameters: d.parameters,
    issues: d.issues.map((i) => ({
      code: i.code,
      message: i.message,
      fieldId: i.field_id,
      ruleId: i.rule_id,
      path: i.path,
    })),
  };
}
