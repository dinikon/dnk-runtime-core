import type {
  SchemaNode,
  SchemaField,
  SchemaCalculation,
  SchemaTransform,
  FeedSchema,
  SavedFeedSchema,
  SaveFeedSchema,
  SchemaMetadata,
  FeedSchemaDefinition,
} from "../model/feed-schema.types.ts";
import type {
  SchemaNodeDTO,
  SchemaFieldDTO,
  CalculationDTO,
  TransformDTO,
  DefinitionDTO,
  FeedSchemaDTO,
  SavedFeedSchemaDTO,
  SaveFeedSchemaDTO,
  FieldTypesDTO,
  SourcePathsDTO,
  TransformsDTO,
} from "./feed-schema.dto.ts";
export function mapNode(node: SchemaNodeDTO): SchemaNode {
  switch (node.kind) {
    case "scalar":
      return { kind: node.kind, valueType: node.value_type, value: node.value };
    case "collection":
      return {
        kind: node.kind,
        itemType: node.item_type,
        items: node.items.map(mapNode),
      };
    case "arithmetic":
      return {
        kind: node.kind,
        operator: node.operator,
        ...(node.left ? { left: mapNode(node.left) } : {}),
        ...(node.right ? { right: mapNode(node.right) } : {}),
        ...(node.operand ? { operand: mapNode(node.operand) } : {}),
      };
    case "function":
      return { ...node, arguments: node.arguments.map(mapNode) };
    case "comparison":
      return { ...node, left: mapNode(node.left), right: mapNode(node.right) };
    case "logical":
      return { ...node, operands: node.operands.map(mapNode) };
    default:
      return { ...node };
  }
}
export function nodePayload(node: SchemaNode): SchemaNodeDTO {
  switch (node.kind) {
    case "scalar":
      return { kind: node.kind, value_type: node.valueType, value: node.value };
    case "collection":
      return {
        kind: node.kind,
        item_type: node.itemType,
        items: node.items.map(nodePayload),
      };
    case "arithmetic":
      return {
        kind: node.kind,
        operator: node.operator,
        ...(node.left ? { left: nodePayload(node.left) } : {}),
        ...(node.right ? { right: nodePayload(node.right) } : {}),
        ...(node.operand ? { operand: nodePayload(node.operand) } : {}),
      };
    case "function":
      return { ...node, arguments: node.arguments.map(nodePayload) };
    case "comparison":
      return {
        ...node,
        left: nodePayload(node.left),
        right: nodePayload(node.right),
      };
    case "logical":
      return { ...node, operands: node.operands.map(nodePayload) };
    default:
      return { ...node };
  }
}
function mapCalculation(value: CalculationDTO): SchemaCalculation {
  return {
    defaultExpression: mapNode(value.default_expression),
    rules: value.rules.map((r) => ({
      id: r.id,
      condition: mapNode(r.condition),
      expression: mapNode(r.expression),
    })),
    purchaseSource: value.purchase_source
      ? {
          provider: value.purchase_source.provider,
          path: value.purchase_source.path,
          selection: {
            mode: value.purchase_source.selection.mode,
            supplierSourceId:
              value.purchase_source.selection.supplier_source_id,
          },
        }
      : null,
  };
}
function calculationPayload(value: SchemaCalculation): CalculationDTO {
  return {
    default_expression: nodePayload(value.defaultExpression),
    rules: value.rules.map((r) => ({
      id: r.id,
      condition: nodePayload(r.condition),
      expression: nodePayload(r.expression),
    })),
    ...(value.purchaseSource && {
      purchase_source: {
        provider: value.purchaseSource.provider,
        path: value.purchaseSource.path,
        selection: {
          mode: value.purchaseSource.selection.mode,
          supplier_source_id: value.purchaseSource.selection.supplierSourceId,
        },
      },
    }),
  };
}
function mapTransform(t: TransformDTO): SchemaTransform {
  return t.op === "string.truncate"
    ? { operation: t.op, parameters: { maxLength: t.params.max_length } }
    : t.op === "money.ceil_step"
      ? { operation: t.op, parameters: { step: t.params.step } }
      : { operation: t.op, parameters: {} };
}
function transformPayload(t: SchemaTransform): TransformDTO {
  return t.operation === "string.truncate"
    ? { op: t.operation, params: { max_length: t.parameters.maxLength } }
    : t.operation === "money.ceil_step"
      ? { op: t.operation, params: { step: t.parameters.step } }
      : { op: t.operation, params: {} };
}
export function mapSchemaField(field: SchemaFieldDTO): SchemaField {
  const type = field.type_definition;
  const common = {
    id: field.id,
    key: field.key,
    label: field.label,
    export: { ...field.export },
    aiInstruction: field.ai.instruction,
  };
  return {
    ...common,
    typeDefinition:
      type.kind === "money"
        ? {
            kind: type.kind,
            currency: type.currency,
            constraints: {
              required: type.constraints.required,
              minAmount: type.constraints.min_amount,
              maxAmount: type.constraints.max_amount,
            },
            value:
              type.value.mode === "CALCULATED"
                ? {
                    kind: "MONEY",
                    mode: "CALCULATED",
                    calculation: mapCalculation(type.value.calculation),
                  }
                : structuredClone(type.value),
            transforms: type.transforms.map(mapTransform),
          }
        : {
            kind: type.kind,
            locale: type.locale,
            fallbackPolicy: structuredClone(type.fallback_policy),
            constraints: {
              required: type.constraints.required,
              minLength: type.constraints.min_length,
              maxLength: type.constraints.max_length,
            },
            value: structuredClone(type.value),
            transforms: type.transforms.map(mapTransform),
          },
  };
}
export function schemaFieldPayload(field: SchemaField): SchemaFieldDTO {
  const type = field.typeDefinition;
  return {
    id: field.id,
    key: field.key,
    label: field.label,
    export: { ...field.export },
    ai: { instruction: field.aiInstruction },
    type_definition:
      type.kind === "money"
        ? {
            kind: type.kind,
            currency: type.currency,
            constraints: {
              required: type.constraints.required,
              min_amount: type.constraints.minAmount,
              max_amount: type.constraints.maxAmount,
            },
            value:
              type.value.mode === "CALCULATED"
                ? {
                    kind: "MONEY",
                    mode: "CALCULATED",
                    calculation: calculationPayload(type.value.calculation),
                  }
                : structuredClone(type.value),
            transforms: type.transforms.map(transformPayload),
          }
        : {
            kind: type.kind,
            locale: type.locale,
            fallback_policy: structuredClone(type.fallbackPolicy),
            constraints: {
              required: type.constraints.required,
              min_length: type.constraints.minLength,
              max_length: type.constraints.maxLength,
            },
            value: structuredClone(type.value),
            transforms: type.transforms.map(transformPayload),
          },
  };
}
export function mapDefinition(value: DefinitionDTO): FeedSchemaDefinition {
  return {
    schemaFormatVersion: value.schema_format_version,
    fields: value.root.fields.map(mapSchemaField),
  };
}
export function definitionPayload(value: FeedSchemaDefinition): DefinitionDTO {
  return {
    schema_format_version: value.schemaFormatVersion,
    root: {
      key: "publication",
      kind: "object",
      fields: value.fields.map(schemaFieldPayload),
    },
  };
}
export function mapFeedSchema(value: FeedSchemaDTO): FeedSchema {
  return {
    feedId: value.feed_id,
    version: value.version,
    status: value.status,
    definition: mapDefinition(value.definition),
  };
}
export function mapSavedSchema(value: SavedFeedSchemaDTO): SavedFeedSchema {
  return {
    feedId: value.feed_id,
    version: value.version,
    definition: mapDefinition(value.definition),
  };
}
export function saveSchemaPayload(value: SaveFeedSchema): SaveFeedSchemaDTO {
  return {
    expected_version: value.expectedVersion,
    definition: definitionPayload(value.definition),
  };
}
export function mapSchemaMetadata(
  types: FieldTypesDTO,
  sources: SourcePathsDTO,
  transforms: TransformsDTO,
): SchemaMetadata {
  return {
    fieldTypes: types.items.map((t) => ({
      kind: t.kind,
      label: t.label,
      supportsLocale: t.supports_locale,
      supportsCurrency: t.supports_currency,
      editableModes: [...t.editable_modes],
    })),
    locales: types.locales.map((l) => ({ ...l })),
    maxFields: types.max_fields,
    maxTransforms: types.max_transforms,
    sources: sources.items.map((s) => ({
      provider: s.provider,
      path: s.path,
      label: s.label,
      fieldKinds: [...s.field_kinds],
      requiresLocale: s.requires_locale,
    })),
    transforms: transforms.items.map((t) => ({
      operation: t.operation,
      label: t.label,
      fieldKinds: [...t.field_kinds],
      parameterKind: t.parameter_kind,
    })),
  };
}
