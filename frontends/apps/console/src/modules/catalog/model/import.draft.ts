import type { ImportConfiguration, ImportMapping } from "./import.types";
export function cloneImportConfiguration(
  value: ImportConfiguration,
): ImportConfiguration {
  return {
    ...value,
    mappings: value.mappings.map((mapping) => ({ ...mapping })),
  };
}
export function importConfigurationEquals(
  left: ImportConfiguration,
  right: ImportConfiguration,
): boolean {
  return JSON.stringify(left) === JSON.stringify(right);
}
export function newImportMapping(): ImportMapping {
  return { target: "title", source: null, constant: "", locale: null };
}

export function acknowledgeImportConfiguration(
  current: ImportConfiguration,
  previous: ImportConfiguration,
  submitted: ImportConfiguration | null,
  confirmed: ImportConfiguration,
): ImportConfiguration {
  const unchanged = importConfigurationEquals(current, previous);
  const sent =
    submitted !== null && importConfigurationEquals(current, submitted);
  return cloneImportConfiguration(unchanged || sent ? confirmed : current);
}
export function importMappingPreview(
  configuration: ImportConfiguration,
  values: Record<string, string[]>,
): Record<string, string[]> {
  const output: Record<string, string[]> = {};
  for (const mapping of configuration.mappings) {
    const source =
      mapping.constant !== null
        ? [mapping.constant]
        : values[mapping.source ?? ""];
    if (!source || (!configuration.clearEmpty && !source.some((v) => v.trim())))
      continue;
    const key = mapping.locale
      ? `${mapping.target} (${mapping.locale})`
      : mapping.target;
    output[key] = [...source];
  }
  return output;
}
