import type { CategoryTypeDTO, CategoryDocumentExportDTO, CategoryPublicationExportDTO } from "./feed-categories.dto";
import type {
  FieldKind,
  SourcePath,
  SchemaNode,
  SchemaSource,
  SchemaMetadata,
  NodeForms,
} from "../model/feed-schema.types";
import type { FeedStatus } from "../model/feed.types";
export type SchemaNodeDTO =
  | { kind: "parameter"; parameter: string }
  | { kind: "decimal"; value: string }
  | {
      kind: "scalar";
      value_type: "uuid" | "string" | "boolean";
      value: string | boolean;
    }
  | {
      kind: "collection";
      item_type: "uuid" | "string" | "boolean";
      items: SchemaNodeDTO[];
    }
  | {
      kind: "arithmetic";
      operator: Extract<SchemaNode, { kind: "arithmetic" }>["operator"];
      left?: SchemaNodeDTO;
      right?: SchemaNodeDTO;
      operand?: SchemaNodeDTO;
    }
  | {
      kind: "function";
      function: "MIN" | "MAX" | "ABS";
      arguments: SchemaNodeDTO[];
    }
  | {
      kind: "comparison";
      operator: Extract<SchemaNode, { kind: "comparison" }>["operator"];
      left: SchemaNodeDTO;
      right: SchemaNodeDTO;
    }
  | {
      kind: "logical";
      operator: "ALL" | "ANY" | "NOT";
      operands: SchemaNodeDTO[];
    }
  | { kind: "presence"; operator: "EXISTS" | "IS_MISSING"; parameter: string };
export interface CalculationDTO {
  default_expression: SchemaNodeDTO;
  rules: { id: string; condition: SchemaNodeDTO; expression: SchemaNodeDTO }[];
  purchase_source?: {
    provider: "supplier_sourcing";
    path: "purchase_price";
    selection: { mode: "SUPPLIER_SOURCE"; supplier_source_id: string };
  } | null;
}
export type TransformDTO =
  | { op: "string.trim"; params: Record<string, never> }
  | { op: "string.truncate"; params: { max_length: number } }
  | { op: "money.ceil_step"; params: { step: string } };
type DirectValueDTO = { kind: "SOURCE"; source: SchemaSource } | { kind: "MANUAL" };

export type FieldTypeDTO =
  | CategoryTypeDTO
  | {
      kind: "integer";
      value: DirectValueDTO | { kind: "CONSTANT"; value: number };
      constraints: { required: boolean; min_value: number | null; max_value: number | null };
    }
  | {
      kind: "boolean";
      value: DirectValueDTO | { kind: "CONSTANT"; value: boolean }
        | { kind: "CALCULATED"; condition: SchemaNodeDTO; then_value: boolean; else_value: boolean };
      constraints: { required: boolean };
    }
  | {
      kind: "string" | "text" | "rich_text";
      locale: string | null;
      fallback_policy: {
        mode: "NONE" | "LOCALE_CHAIN" | "MANUAL_REQUIRED";
        locales: string[];
      } | null;
      constraints: {
        required: boolean;
        min_length: number | null;
        max_length: number | null;
      };
      value: DirectValueDTO | { kind: "CONSTANT"; value: string };
      transforms: TransformDTO[];
    }
  | {
      kind: "money";
      currency: string | null;
      constraints: {
        required: boolean;
        min_amount: string | null;
        max_amount: string | null;
      };
      value:
        | { kind: "MONEY"; mode: "SOURCE"; source: SchemaSource }
        | { kind: "MONEY"; mode: "MANUAL" }
        | { kind: "MONEY"; mode: "CALCULATED"; calculation: CalculationDTO };
      transforms: TransformDTO[];
    };
interface FieldExportDTO {
  name: string;
  enabled: boolean;
  xml_placement?: "ELEMENT" | "ATTRIBUTE";
  document?: CategoryDocumentExportDTO;
  publication?: CategoryPublicationExportDTO;
}
type FieldDataDTO<T extends FieldTypeDTO = FieldTypeDTO> =
  T extends FieldTypeDTO ? Omit<T, "kind"> : never;
export interface GraphFieldDTO {
  id: string;
  key: string;
  name: string;
  typeId: string;
  typeVersion: number;
  scope: "offer";
  forms?: NodeForms;
  data: FieldDataDTO | { source: "feed"; treeId: string };
  export: FieldExportDTO;
  aiInstruction: string | null;
}
export interface GraphDefinitionDTO {
  schema_format_version: 2;
  fields: GraphFieldDTO[];
  categoryTrees?: { id: string; data: Omit<CategoryTypeDTO, "kind"> }[];
}
export interface FeedSchemaDTO {
  feed_id: string;
  version: number;
  status: FeedStatus;
  definition: GraphDefinitionDTO;
}
export interface SavedFeedSchemaDTO {
  feed_id: string;
  version: number;
  definition: GraphDefinitionDTO;
}
export interface SaveFeedSchemaDTO {
  expected_version: number;
  definition: GraphDefinitionDTO;
}
export interface FieldTypesDTO {
  items: {
    kind: FieldKind;
    label: string;
    supports_locale: boolean;
    supports_currency: boolean;
    editable_modes: string[];
    type_id?: string;
    type_version?: number;
    forms?: NodeForms;
  }[];
  locales: { code: string; name: string }[];
  max_fields: number;
  max_transforms: number;
}
export interface SourcePathsDTO {
  items: {
    provider: "catalog";
    path: SourcePath;
    label: string;
    field_kinds: FieldKind[];
    requires_locale: boolean;
  }[];
}
export interface TransformsDTO {
  items: {
    operation: SchemaMetadata["transforms"][number]["operation"];
    label: string;
    field_kinds: FieldKind[];
    parameter_kind: "none" | "max_length" | "step";
  }[];
}
