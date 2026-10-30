import type { LocationQuery, LocationQueryRaw } from "vue-router";

export type PublicationDetailsTab = "positions" | "bindings";
export function publicationDetailsTab(
  query: LocationQuery,
): PublicationDetailsTab {
  const editingBinding =
    typeof query.binding === "string" && query.binding.length > 0;
  return editingBinding || query.publication_tab === "bindings"
    ? "bindings"
    : "positions";
}
/** Список сохраняет свои фильтры, а состояние открытой карточки и её редактора снимается. */
export function publicationListQuery(query: LocationQuery): LocationQueryRaw {
  const result: LocationQueryRaw = { ...query };
  for (const key of [
    "publication_tab",
    "binding",
    "binding_channel",
    "binding_offset",
    "binding_limit",
  ])
    delete result[key];
  return result;
}
export function publicationLinkQuery(
  query: LocationQuery,
  channelId: string,
): LocationQueryRaw {
  return {
    ...publicationListQuery(query),
    publication_tab: "bindings",
    binding: "new",
    binding_channel: channelId,
  };
}
