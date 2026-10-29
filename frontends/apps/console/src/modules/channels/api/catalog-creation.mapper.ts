import type { CreatePublicationCatalogResponse } from "./catalog-creation.dto";
import type { CreatePublicationCatalogResult } from "../model/catalog-creation.types";
export function publicationCatalogFromDto(
  value: CreatePublicationCatalogResponse,
): CreatePublicationCatalogResult {
  return {
    catalogItemId: value.catalog_item_id,
    bindingGroupId: value.binding_group_id,
    created: value.created,
    warnings: [...value.warnings],
  };
}
