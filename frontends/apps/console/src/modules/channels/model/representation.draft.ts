import type {
  RepresentationOverrides,
  LocalizedOverrides,
  RepresentationDetails,
  RepresentationVersion,
} from "./representation.types";

function normalizedFields(value: LocalizedOverrides): LocalizedOverrides {
  return {
    ...(value.title != null ? { title: value.title } : {}),
    ...(value.body != null ? { body: value.body } : {}),
    ...(value.gallery != null
      ? { gallery: value.gallery.map((image) => ({ ...image })) }
      : {}),
  };
}
export function normalizeRepresentationOverrides(
  value: RepresentationOverrides,
): RepresentationOverrides {
  const common: RepresentationOverrides["common"] = {};
  const items: RepresentationOverrides["items"] = {};
  for (const locale of Object.keys(value.common).sort()) {
    const fields = normalizedFields(value.common[locale]!);
    if (Object.keys(fields).length) common[locale] = fields;
  }
  for (const id of Object.keys(value.items).sort()) {
    const localized: Record<string, LocalizedOverrides> = {};
    for (const locale of Object.keys(value.items[id]!).sort()) {
      const fields = normalizedFields(value.items[id]![locale]!);
      if (Object.keys(fields).length) localized[locale] = fields;
    }
    if (Object.keys(localized).length) items[id] = localized;
  }
  return { common, items };
}
export function representationDraftKey(value: RepresentationOverrides): string {
  return JSON.stringify(normalizeRepresentationOverrides(value));
}
export function representationVersion(
  value: RepresentationDetails,
): RepresentationVersion {
  return {
    expectedRevision: value.state.revision,
    expectedBindingRevision: value.bindingRevision,
    expectedConfigRevision: value.configRevision,
  };
}
