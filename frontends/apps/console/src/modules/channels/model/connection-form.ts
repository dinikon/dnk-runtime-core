import type {
  Connection,
  ConnectionFormValues,
  ConnectionSettings,
  Platform,
} from "./channels.types";
import {
  defaultSettings,
  settingsIssue,
  settingsSchemaSupported,
} from "./settings-schema.ts";
export function connectionFormValues(
  platform: Platform,
  connection: Connection | undefined,
): ConnectionFormValues {
  return {
    endpoint:
      connection?.endpoint ??
      platform.endpointSchema.const ??
      platform.endpointSchema.default ??
      "",
    settings: connection
      ? JSON.parse(JSON.stringify(connection.settings))
      : defaultSettings(platform.settingsSchema),
    replaceCredentials: !connection,
    credentials: Object.fromEntries(
      Object.keys(platform.credentialsSchema.properties ?? {}).map((key) => [
        key,
        "",
      ]),
    ),
  };
}
export function connectionSettings(
  values: ConnectionFormValues,
): ConnectionSettings {
  return {
    endpoint: values.endpoint.trim(),
    options: JSON.parse(JSON.stringify(values.settings)),
  };
}
export function settingsSignature(settings: ConnectionSettings): string {
  function stable(value: unknown): unknown {
    if (Array.isArray(value)) return value.map(stable);
    if (value && typeof value === "object")
      return Object.fromEntries(
        Object.entries(value)
          .sort(([left], [right]) => left.localeCompare(right))
          .map(([key, item]) => [key, stable(item)]),
      );
    return value;
  }
  return JSON.stringify(stable(settings));
}
export function validateConnectionForm(
  values: ConnectionFormValues,
  platform: Platform,
  needsCredentials: boolean,
): string | null {
  if (!settingsSchemaSupported(platform.settingsSchema))
    return "Конфигурация формы платформы не поддерживается.";
  const issue = settingsIssue(platform.settingsSchema, values.settings);
  if (issue) return issue;
  try {
    const url = new URL(values.endpoint);
    if (
      url.protocol !== "https:" ||
      url.username ||
      url.password ||
      url.search ||
      url.hash ||
      (url.port && url.port !== "443")
    )
      return "Укажите HTTPS-адрес без логина, параметров и фрагмента.";
  } catch {
    return "Укажите корректный HTTPS-адрес.";
  }
  if (
    platform.endpointSchema.const &&
    values.endpoint !== platform.endpointSchema.const
  )
    return "Адрес этого источника фиксирован.";
  if (needsCredentials)
    for (const key of platform.credentialsSchema.required ?? [])
      if (!values.credentials[key]?.trim())
        return "Заполните обязательные поля доступа.";
  return null;
}
