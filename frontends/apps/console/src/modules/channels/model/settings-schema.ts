import type {
  JsonValue,
  SettingsObject,
  SettingsSchema,
} from "./channels.types";

const supportedKeys = new Set([
  "type",
  "title",
  "description",
  "properties",
  "required",
  "additionalProperties",
  "items",
  "prefixItems",
  "minItems",
  "maxItems",
  "uniqueItems",
  "minLength",
  "maxLength",
  "pattern",
  "minimum",
  "maximum",
  "enum",
  "const",
  "default",
  "x-reference",
]);
export function settingsSchemaSupported(
  schema: SettingsSchema | undefined,
): boolean {
  if (!schema || Object.keys(schema).some((key) => !supportedKeys.has(key)))
    return false;
  if (
    !["object", "array", "string", "boolean", "number", "integer"].includes(
      schema.type ?? "",
    )
  )
    return false;
  if (schema.type === "object")
    return (
      schema.additionalProperties !== true &&
      Object.values(schema.properties ?? {}).every(settingsSchemaSupported) &&
      (schema.required ?? []).every((key) => key in (schema.properties ?? {}))
    );
  if (schema.type === "array")
    return (
      !!schema.items &&
      settingsSchemaSupported(schema.items) &&
      (schema.prefixItems ?? []).every(settingsSchemaSupported)
    );
  return (
    !schema["x-reference"] ||
    ["locale", "currency"].includes(schema["x-reference"])
  );
}
export function schemaDefault(schema: SettingsSchema): JsonValue {
  if (schema.const !== undefined)
    return JSON.parse(JSON.stringify(schema.const));
  if (schema.default !== undefined)
    return JSON.parse(JSON.stringify(schema.default));
  if (schema.type === "object")
    return Object.fromEntries(
      Object.entries(schema.properties ?? {})
        .filter(
          ([key, value]) =>
            schema.required?.includes(key) ||
            value.default !== undefined ||
            value.const !== undefined,
        )
        .map(([key, value]) => [key, schemaDefault(value)]),
    );
  if (schema.type === "array")
    return Array.from({ length: schema.minItems ?? 0 }, (_, index) =>
      schemaDefault(arrayItemSchema(schema, index)),
    );
  if (schema.type === "boolean") return false;
  return "";
}
export function arrayItemSchema(
  schema: SettingsSchema,
  index: number,
): SettingsSchema {
  const field = { ...schema.items, ...schema.prefixItems?.[index] };
  return {
    ...field,
    title: field.title ?? `${schema.title ?? "Значение"} ${index + 1}`,
  };
}

export function settingsIssue(
  schema: SettingsSchema,
  value: JsonValue | undefined,
  path = "Настройки",
  required = true,
): string | null {
  if (value === undefined || value === "")
    return required ? `Заполните поле «${path}».` : null;
  if (
    schema.const !== undefined &&
    JSON.stringify(value) !== JSON.stringify(schema.const)
  )
    return `Поле «${path}» имеет фиксированное значение.`;
  if (
    schema.enum &&
    !schema.enum.some((item) => JSON.stringify(item) === JSON.stringify(value))
  )
    return `Выберите допустимое значение «${path}».`;
  if (schema.type === "object") {
    if (value === null || Array.isArray(value) || typeof value !== "object")
      return `Некорректный объект «${path}».`;
    if (Object.keys(value).some((key) => !(key in (schema.properties ?? {}))))
      return `Неизвестные поля в «${path}».`;
    for (const [key, child] of Object.entries(schema.properties ?? {})) {
      const issue = settingsIssue(
        child,
        value[key],
        child.title ?? key,
        schema.required?.includes(key) ?? false,
      );
      if (issue) return issue;
    }
  } else if (schema.type === "array") {
    if (
      !Array.isArray(value) ||
      value.length < (schema.minItems ?? 0) ||
      value.length > (schema.maxItems ?? Infinity)
    )
      return `Проверьте число значений «${path}».`;
    if (
      schema.uniqueItems &&
      new Set(value.map((item) => JSON.stringify(item))).size !== value.length
    )
      return `Значения «${path}» должны отличаться.`;
    for (let i = 0; i < value.length; i++) {
      const issue = settingsIssue(
        arrayItemSchema(schema, i),
        value[i],
        arrayItemSchema(schema, i).title ?? path,
      );
      if (issue) return issue;
    }
  } else if (schema.type === "string") {
    if (
      typeof value !== "string" ||
      value.length < (schema.minLength ?? 0) ||
      value.length > (schema.maxLength ?? Infinity) ||
      (schema.pattern && !new RegExp(schema.pattern).test(value))
    )
      return `Проверьте значение «${path}».`;
  } else if (schema.type === "boolean") {
    if (typeof value !== "boolean") return `Выберите значение «${path}».`;
  } else if (
    typeof value !== "number" ||
    !Number.isFinite(value) ||
    (schema.type === "integer" && !Number.isSafeInteger(value)) ||
    value < (schema.minimum ?? -Infinity) ||
    value > (schema.maximum ?? Infinity)
  )
    return `Проверьте число «${path}».`;
  return null;
}
export function defaultSettings(schema: SettingsSchema): SettingsObject {
  return schemaDefault(schema) as SettingsObject;
}
