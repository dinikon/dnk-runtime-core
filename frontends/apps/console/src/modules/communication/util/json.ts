import type {
  CommunicationJsonSchema,
  JsonObject,
  JsonValue,
} from "@/modules/communication/api";

export function schemaType(schema: CommunicationJsonSchema | null | undefined) {
  const rawType = schema?.type;

  if (Array.isArray(rawType)) {
    return rawType.find((type) => type !== "null") ?? "string";
  }

  return rawType ?? "string";
}

export function buildJsonSchemaDefaults(
  schema: CommunicationJsonSchema | null | undefined,
): JsonObject {
  const defaults: JsonObject = {};
  const properties = schema?.properties ?? {};

  for (const [key, propertySchema] of Object.entries(properties)) {
    defaults[key] = defaultValueForSchema(propertySchema);
  }

  return defaults;
}

export function defaultValueForSchema(
  schema: CommunicationJsonSchema,
): JsonValue {
  if (schema.default !== undefined) {
    return schema.default;
  }

  if (schema.enum?.length) {
    return schema.enum[0];
  }

  const type = schemaType(schema);

  if (type === "boolean") {
    return false;
  }

  if (type === "integer" || type === "number") {
    return 0;
  }

  if (type === "object") {
    return buildJsonSchemaDefaults(schema);
  }

  return "";
}

export function compactJsonObject(value: JsonObject): JsonObject {
  const result: JsonObject = {};

  for (const [key, item] of Object.entries(value)) {
    if (item === "" || item === null) {
      continue;
    }

    result[key] = item;
  }

  return result;
}

export function parseJsonObject(text: string, fallback: JsonObject = {}) {
  const trimmed = text.trim();

  if (!trimmed) {
    return fallback;
  }

  const parsed = JSON.parse(trimmed) as unknown;

  if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
    throw new Error("JSON value must be an object.");
  }

  return parsed as JsonObject;
}

export function formatJsonObject(value: JsonObject) {
  return JSON.stringify(value, null, 2);
}
