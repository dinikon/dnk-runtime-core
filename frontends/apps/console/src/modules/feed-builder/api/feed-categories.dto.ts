import type { SchemaNodeDTO, TransformDTO } from "./feed-schema.dto";

export interface CategoryTypeDTO {
  kind: "category";
  locale: string;
  name_transforms: TransformDTO[];
  object_schema: {
    id_key: string;
    label_key: string;
    fields: {
      key: string;
      kind: "string" | "text" | "integer" | "boolean";
      required: boolean;
      xml: { name: string; placement: "ATTRIBUTE" | "ELEMENT" | "TEXT" | "NONE" };
      source: "CATALOG_NAME" | null;
    }[];
  };
  value: {
    kind: "INLINE";
    nodes: {
      id: string;
      values: Record<string, string | number | boolean>;
      parent_id: string | null;
      catalog_id: string | null;
      inherit_parent: boolean;
    }[];
    rules: { id: string; target_id: string; label: string; condition: SchemaNodeDTO; include_descendants: boolean }[];
    fallback: "CATALOG" | "FIXED" | "NONE";
    fallback_id: string | null;
    catalog_priority: string[];
    next_export_id: number;
  };
}

export interface CategoryDocumentExportDTO {
  container: string;
  item: string;
  parent: "ROOT" | "SHOP";
  layout: "FLAT" | "NESTED";
  parent_attribute: string;
}

export interface CategoryPublicationExportDTO {
  value_key: string;
  required: boolean;
}

export interface PreviewCategoryDTO {
  field_id: string;
  field_label: string;
  node_id: string;
  export_id: string;
  path: string[];
  rule_label: string | null;
}
