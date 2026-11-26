import type { CategoryTypeDTO } from "./feed-categories.dto";
import type { CategoryType } from "../model/feed-categories.types";
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
  FieldTypeDTO,
  CalculationDTO,
  TransformDTO,
  DefinitionDTO,
  GraphFieldDTO,
  GraphDefinitionDTO,
  FeedSchemaDTO,
  SavedFeedSchemaDTO,
  SaveFeedSchemaDTO,
  FieldTypesDTO,
  SourcePathsDTO,
  TransformsDTO,
} from "./feed-schema.dto.ts";
import { cloneSchemaValue } from "../model/feed-schema.clone.ts";

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
    export: {
      name: field.export.name,
      enabled: field.export.enabled,
      xmlPlacement: field.export.xml_placement ?? "ELEMENT",
      ...(field.export.document ? { document: {
        container: field.export.document.container, item: field.export.document.item,
        parent: field.export.document.parent, layout: field.export.document.layout,
        parentAttribute: field.export.document.parent_attribute,
      } } : {}),
      ...(field.export.publication ? { publication: {
        valueKey: field.export.publication.value_key, required: field.export.publication.required,
      } } : {}),
    },
    aiInstruction: field.ai.instruction,
  };
  if (type.kind === "category") return { ...common, typeDefinition: mapCategory(type) };
  if (type.kind === "integer") {
    return { ...common, typeDefinition: {
      kind: type.kind, value: cloneSchemaValue(type.value),
      constraints: {
        required: type.constraints.required,
        minValue: type.constraints.min_value, maxValue: type.constraints.max_value,
      },
    } };
  }
  if (type.kind === "boolean") {
    const value = type.value;
    return { ...common, typeDefinition: {
      kind: type.kind,
      constraints: { ...type.constraints },
      value: value.kind === "CALCULATED" ? {
        kind: value.kind, condition: mapNode(value.condition),
        thenValue: value.then_value, elseValue: value.else_value,
      } : cloneSchemaValue(value),
    } };
  }
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
  const common = {
    id: field.id,
    key: field.key,
    label: field.label,
    export: {
      name: field.export.name,
      enabled: field.export.enabled,
      ...(field.export.xmlPlacement === "ATTRIBUTE"
        ? { xml_placement: field.export.xmlPlacement }
        : {}),
      ...(field.export.document ? { document: {
        container: field.export.document.container, item: field.export.document.item,
        parent: field.export.document.parent, layout: field.export.document.layout,
        parent_attribute: field.export.document.parentAttribute,
      } } : {}),
      ...(field.export.publication ? { publication: {
        value_key: field.export.publication.valueKey, required: field.export.publication.required,
      } } : {}),
    },
    ai: { instruction: field.aiInstruction },
  };
  if (type.kind === "category") return { ...common, type_definition: categoryPayload(type) };
  if (type.kind === "integer") {
    return { ...common, type_definition: {
      kind: type.kind, value: cloneSchemaValue(type.value),
      constraints: {
        required: type.constraints.required,
        min_value: type.constraints.minValue, max_value: type.constraints.maxValue,
      },
    } };
  }
  if (type.kind === "boolean") {
    const value = type.value;
    return { ...common, type_definition: {
      kind: type.kind,
      constraints: { ...type.constraints },
      value: value.kind === "CALCULATED" ? {
        kind: value.kind, condition: nodePayload(value.condition),
        then_value: value.thenValue, else_value: value.elseValue,
      } : cloneSchemaValue(value),
    } };
  }
  return {
    ...common,
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
function mapCategory(type: CategoryTypeDTO): CategoryType {
  const value = type.value;
  return {
    kind: type.kind, locale: type.locale, nameTransforms: type.name_transforms.map(mapTransform),
    objectSchema: {
      idKey: type.object_schema.id_key, labelKey: type.object_schema.label_key,
      fields: cloneSchemaValue(type.object_schema.fields),
    },
    value: {
      kind: value.kind, nextExportId: value.next_export_id,
      nodes: value.nodes.map((node) => ({
        id: node.id, parentId: node.parent_id, catalogId: node.catalog_id,
        inheritParent: node.inherit_parent, values: { ...node.values },
      })),
      rules: value.rules.map((rule) => ({
        id: rule.id, targetId: rule.target_id, label: rule.label,
        condition: mapNode(rule.condition), includeDescendants: rule.include_descendants,
      })),
      fallback: value.fallback, fallbackId: value.fallback_id, catalogPriority: [...value.catalog_priority],
    },
  };
}

function categoryTreePayload(type: CategoryType): Omit<CategoryTypeDTO, "kind"> {
  const value = type.value;
  return {
    locale: type.locale, name_transforms: type.nameTransforms.map(transformPayload),
    object_schema: {
      id_key: type.objectSchema.idKey, label_key: type.objectSchema.labelKey,
      fields: cloneSchemaValue(type.objectSchema.fields),
    },
    value: {
      kind: value.kind, next_export_id: value.nextExportId,
      nodes: value.nodes.map((node) => ({
        id: node.id, parent_id: node.parentId, catalog_id: node.catalogId,
        inherit_parent: node.inheritParent, values: { ...node.values },
      })),
      rules: value.rules.map((rule) => ({
        id: rule.id, target_id: rule.targetId, label: rule.label,
        condition: nodePayload(rule.condition), include_descendants: rule.includeDescendants,
      })),
      fallback: value.fallback, fallback_id: value.fallbackId, catalog_priority: [...value.catalogPriority],
    },
  };
}

function categoryPayload(type: CategoryType): CategoryTypeDTO {
  return { kind: type.kind, ...categoryTreePayload(type) };
}

const nodeIds = {
  string: "core.short_text",
  text: "core.long_text",
  money: "core.money",
  integer: "core.integer",
  boolean: "core.boolean",
  category: "core.category_reference",
} satisfies Record<SchemaField["typeDefinition"]["kind"], string>;

function mapGraphField(
  node: GraphFieldDTO, trees: NonNullable<GraphDefinitionDTO["categoryTrees"]>,
): SchemaField {
  const kind = (Object.keys(nodeIds) as (keyof typeof nodeIds)[]).find(
    (kind) => nodeIds[kind] === node.typeId,
  );
  if (!kind || node.typeVersion !== 1)
    throw new Error("Тип ноды недоступен в текущей версии Console.");
  const treeId = "treeId" in node.data ? node.data.treeId : undefined;
  const source = treeId ? trees.find((tree) => tree.id === treeId) : undefined;
  if (kind === "category" && !source)
    throw new Error("Дерево категорий этой ноды отсутствует.");
  return {
    ...mapSchemaField({
    id: node.id,
    key: node.key,
    label: node.name,
    type_definition: { ...(source?.data ?? node.data), kind } as FieldTypeDTO,
    export: node.export,
    ai: { instruction: node.aiInstruction },
    }),
    ...(treeId ? { categoryTreeId: treeId } : {}),
  };
}

export function mapDefinition(value: DefinitionDTO): FeedSchemaDefinition {
  if (value.schema_format_version === 2) {
    const trees = value.categoryTrees ?? [];
    return {
      schemaFormatVersion: 2,
      fields: value.fields.map((node) => mapGraphField(node, trees)),
      categoryTrees: trees.map(({ id, data }) => ({
        id, settings: mapCategory({ ...data, kind: "category" }),
      })),
    };
  }
  return { schemaFormatVersion: 1, fields: value.root.fields.map(mapSchemaField) };
}
export function definitionPayload(value: FeedSchemaDefinition): DefinitionDTO {
  if (value.schemaFormatVersion === 2) {
    const trees = new Map<string, Omit<CategoryTypeDTO, "kind">>(
      value.categoryTrees?.map(({ id, settings }) => [id, categoryTreePayload(settings)]),
    );
    const graphFields = value.fields.map((model): GraphFieldDTO => {
      const field = schemaFieldPayload(model);
      const { kind, ...data } = field.type_definition;
      const node = {
        id: field.id,
        key: field.key,
        name: field.label,
        typeId: nodeIds[kind],
        typeVersion: 1,
        scope: "offer" as const,
        data,
        export: field.export,
        aiInstruction: field.ai.instruction,
      };
      if (model.typeDefinition.kind === "category") {
        const treeId = model.categoryTreeId ?? field.id;
        trees.set(treeId, categoryTreePayload(model.typeDefinition));
        return { ...node, data: { source: "feed", treeId } };
      }
      return node;
    });
    return {
      schema_format_version: 2,
      fields: graphFields,
      categoryTrees: Array.from(trees, ([id, data]) => ({ id, data })),
    };
  }
  return {
    schema_format_version: 1,
    root: { key: "publication", kind: "object", fields: value.fields.map(schemaFieldPayload) },
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
      typeId: t.type_id,
      typeVersion: t.type_version,
      forms: t.forms,
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
