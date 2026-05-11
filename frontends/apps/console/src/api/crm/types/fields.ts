export interface ContactFieldOption {
    value: string;
    label: string;
}

export interface ContactFieldDescription {
    id: string;
    field_name: string;
    label: string;
    description: string;
    type: string;
    kind: string;
    is_nullable: boolean;
    default_value: string | null;
    options: ContactFieldOption[];
}

export interface ContactObjectDescription {
    id: string;
    singular_label: string;
    plural_label: string;
    description: string;
    kind: string;
}

export interface ContactFieldsResponse {
    object: ContactObjectDescription;
    fields: ContactFieldDescription[];
}
