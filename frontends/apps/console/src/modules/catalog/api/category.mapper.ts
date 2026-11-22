import type { CategoryRowDTO } from "./category.dto";
import type { CatalogCategory } from "../model/category.types";

export function categoryFromDto(value: CategoryRowDTO): CatalogCategory {
  return {
    id: value.id,
    parentId: value.parent_id,
    sourceLocale: value.source_locale,
    sourceName: value.source_name,
    name: value.name,
    isDefault: value.is_default,
  };
}
