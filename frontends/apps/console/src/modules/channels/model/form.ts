import type { ConnectionSchema } from "./types";
// Only this declared schema subset is supported. Unknown structures fail closed.
export function supportedSchema(
  connection: ConnectionSchema | null | undefined,
): connection is ConnectionSchema {
  if (!connection || !Array.isArray(connection.ui_schema)) return false;
  const s = connection.json_schema;
  if (
    !s ||
    s.type !== "object" ||
    s.additionalProperties !== false ||
    !s.properties ||
    typeof s.properties !== "object" ||
    Array.isArray(s.properties) ||
    !Array.isArray(s.required)
  )
    return false;
  if (
    Object.keys(s).some(
      (k) =>
        ![
          "$schema",
          "type",
          "properties",
          "required",
          "additionalProperties",
        ].includes(k),
    )
  )
    return false;
  if (
    connection.ui_schema.some(
      (f) =>
        !f ||
        typeof f.property !== "string" ||
        typeof f.widget !== "string" ||
        typeof f.help_text !== "string",
    )
  )
    return false;
  const fields = connection.ui_schema.map((f) => f.property);
  return (
    new Set(fields).size === fields.length &&
    fields.length === Object.keys(s.properties).length &&
    s.required.every((k) => fields.includes(k)) &&
    connection.ui_schema.every((f) => {
      const p = s.properties[f.property];
      return (
        p &&
        typeof p === "object" &&
        !Array.isArray(p) &&
        (p.minLength === undefined ||
          (Number.isInteger(p.minLength) && p.minLength >= 0)) &&
        (p.maxLength === undefined ||
          (Number.isInteger(p.maxLength) &&
            p.maxLength >= (p.minLength ?? 0))) &&
        (p.writeOnly === undefined || typeof p.writeOnly === "boolean") &&
        p.type === "string" &&
        typeof p.title === "string" &&
        ["text", "url", "password"].includes(f.widget) &&
        (!p.writeOnly || f.widget === "password") &&
        (!p.format || p.format === "https-store-url") &&
        Object.keys(p).every((k) =>
          [
            "type",
            "title",
            "minLength",
            "maxLength",
            "format",
            "writeOnly",
          ].includes(k),
        )
      );
    })
  );
}
export function validateFields(
  schema: ConnectionSchema,
  values: Record<string, string>,
  stored: string[],
  replacing: string[],
) {
  const errors: Record<string, string> = {};
  for (const [key, field] of Object.entries(schema.json_schema.properties)) {
    if (field.writeOnly && stored.includes(key) && !replacing.includes(key))
      continue;
    const value = values[key] ?? "";
    if (
      (schema.json_schema.required.includes(key) && value.length === 0) ||
      value.length < (field.minLength ?? 0)
    )
      errors[key] = "Обязательное поле.";
    else if (value.length > (field.maxLength ?? Infinity))
      errors[key] = "Слишком длинное значение.";
    else if (field.format === "https-store-url") {
      try {
        const url = new URL(value);
        if (
          !value.startsWith("https://") ||
          !url.hostname ||
          url.username ||
          url.password ||
          value.includes("?") ||
          value.includes("#") ||
          /[\s\\]/.test(value)
        )
          throw new Error();
      } catch {
        errors[key] =
          "Укажите HTTPS-адрес магазина без параметров и ключей доступа.";
      }
    }
  }
  return errors;
}
