export type ObjectKind = "standard" | "custom" | "system" | "view" | string;

export type FieldType =
    | "uuid"
    | "text"
    | "int"
    | "decimal"
    | "bool"
    | "date"
    | "datetime"
    | "json"
    | "select"
    | "multiselect"
    | string;

export interface RuntimeFieldOption {
    value: string;
    label: string;
}

export interface RuntimeField {
    id: string;
    field_name: string;
    label: string;
    description: string;
    type: FieldType;
    kind: string;
    is_nullable: boolean;
    default_value: string | null;
    options: RuntimeFieldOption[];
}

export interface RuntimeObject {
    id: string;
    created_at: string;
    updated_at: string;
    singular_name: string;
    plural_name: string;
    singular_label: string;
    plural_label: string;
    description: string;
    kind: ObjectKind;
    fields: RuntimeField[];
}

export interface ListObjectsResponse {
    items: RuntimeObject[];
    count: number;
}

export interface CustomFieldInput {
    field_name: string;
    type: FieldType;
    label: string;
    description?: string;
    is_nullable?: boolean;
    default_value?: string | null;
    options?: Record<string, string>;
    settings?: Record<string, string>;
}

export interface CreateCustomObjectPayload {
    singular_name: string;
    plural_name: string;
    singular_label: string;
    plural_label: string;
    description?: string;
    fields?: CustomFieldInput[];
}

export interface CreateCustomFieldPayload {
    object_id: string;
    field: CustomFieldInput;
}

export interface DeleteObjectPayload {
    object_id: string;
}

export interface DeleteFieldPayload {
    object_id: string;
    field_id: string;
}
