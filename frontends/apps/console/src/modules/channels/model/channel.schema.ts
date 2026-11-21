import type { JsonObject, JsonValue, SchemaField } from "./channel.types";
function object(value: JsonValue | undefined): JsonObject {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? value
    : {};
}
function resolved(value: JsonValue | undefined, root: JsonObject): JsonObject {
  const node = object(value);
  const ref = node.$ref;
  return typeof ref === "string" && ref.startsWith("#/$defs/")
    ? object(object(root.$defs)[ref.slice(8)])
    : node;
}
export function schemaFields(
  schema: JsonObject,
  section?: string,
): SchemaField[] {
  const node = section
    ? resolved(object(schema.properties)[section], schema)
    : schema;
  const properties = object(node.properties);
  const required = Array.isArray(node.required) ? node.required : [];
  return Object.entries(properties)
    .filter(([key]) => key !== "version" && key !== "settings")
    .map(([key, raw]) => {
      const field = resolved(raw, schema);
      return {
        key,
        title: typeof field.title === "string" ? field.title : key,
        description:
          typeof field.description === "string" ? field.description : undefined,
        required: required.includes(key),
        secret: field.writeOnly === true || field.format === "password",
        readOnly: field.const !== undefined || field.readOnly === true,
        defaultValue: field.const ?? field.default ?? "",
        options: Array.isArray(field.enum)
          ? field.enum.filter(
              (value): value is string => typeof value === "string",
            )
          : [],
        maxLength:
          typeof field.maxLength === "number" ? field.maxLength : undefined,
        format: typeof field.format === "string" ? field.format : undefined,
      };
    });
}
