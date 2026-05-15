import type {JsonSchemaObject, JsonSchemaProperty} from "@/api/communication";

export interface SchemaField {
    key: string;
    label: string;
    type: string;
    required: boolean;
    property: JsonSchemaProperty;
}

export type SchemaFormValues = Record<string, string | boolean | undefined>;

export function schemaFields(schema: JsonSchemaObject | null | undefined): SchemaField[] {
    const properties = schema?.properties ?? {};
    const required = new Set(schema?.required ?? []);

    return Object.entries(properties).map(([key, property]) => ({
        key,
        label: property.title || key,
        type: property.format === "password" ? "password" : property.type || "string",
        required: required.has(key),
        property
    }));
}

export function initialSchemaForm(schema: JsonSchemaObject | null | undefined): SchemaFormValues {
    return Object.fromEntries(schemaFields(schema).map((field) => [
        field.key,
        initialSchemaFieldValue(field)
    ]));
}

export function coerceSchemaValues(
    schema: JsonSchemaObject | null | undefined,
    values: SchemaFormValues
): Record<string, unknown> {
    const result: Record<string, unknown> = {};

    for (const field of schemaFields(schema)) {
        const rawValue = values[field.key];
        if (rawValue === undefined || rawValue === "") {
            continue;
        }

        if (field.type === "integer") {
            result[field.key] = Number.parseInt(String(rawValue), 10);
        } else if (field.type === "number") {
            result[field.key] = Number(rawValue);
        } else if (field.type === "boolean") {
            result[field.key] = typeof rawValue === "boolean" ? rawValue : rawValue === "true";
        } else {
            result[field.key] = rawValue;
        }
    }

    return result;
}

function initialSchemaFieldValue(field: SchemaField): string | boolean | undefined {
    if (field.property.default === undefined) {
        return field.type === "boolean" ? undefined : "";
    }

    if (field.type === "boolean") {
        return Boolean(field.property.default);
    }

    return String(field.property.default);
}

export function parseJsonObject(value: string, label: string): Record<string, unknown> {
    const trimmed = value.trim();
    if (!trimmed) {
        return {};
    }

    const parsed = JSON.parse(trimmed);
    if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
        throw new Error(`${label} must be a JSON object.`);
    }

    return parsed as Record<string, unknown>;
}
