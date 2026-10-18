import type {
  Connection,
  ConnectionFormValues,
  ConnectionSettings,
  Platform,
} from "./channels.types";
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
    primaryLocale: connection?.locales[0] ?? "",
    secondaryLocale: connection?.locales[1] ?? "",
    currency: connection?.currency ?? "",
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
    locales: [values.primaryLocale, values.secondaryLocale].filter(Boolean),
    currency: values.currency || null,
  };
}
export function settingsSignature(settings: ConnectionSettings): string {
  return JSON.stringify(settings);
}
export function validateConnectionForm(
  values: ConnectionFormValues,
  platform: Platform,
  needsCredentials: boolean,
): string | null {
  if (!values.primaryLocale) return "Выберите основной язык ресурса.";
  if (values.primaryLocale === values.secondaryLocale)
    return "Выберите разные языки.";
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
  if (needsCredentials) {
    for (const key of platform.credentialsSchema.required ?? [])
      if (!values.credentials[key]?.trim())
        return "Заполните обязательные поля доступа.";
  }
  return null;
}
