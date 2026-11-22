import { httpClient } from "@/app/providers/http";
import type { CatalogCategory, CategoryChange } from "../model/category.types";
import type { CategoryRowDTO } from "./category.dto";
import { categoryFromDto } from "./category.mapper";

const base = "/console/catalog/categories";
export async function listCategories(
  locale: string,
  signal?: AbortSignal,
): Promise<CatalogCategory[]> {
  const response = await httpClient.get<{ items: CategoryRowDTO[] }>(base, {
    params: { locale },
    signal,
  });
  return response.data.items.map(categoryFromDto);
}
export async function changeCategory(change: CategoryChange): Promise<void> {
  switch (change.action) {
    case "create":
      await httpClient.post(base, {
        source_locale: change.locale,
        name: change.name,
        parent_id: change.parent,
      });
      return;
    case "update":
      await httpClient.patch(base + "/" + encodeURIComponent(change.id), {
        translations: change.translations,
        parent_id: change.parent,
      });
      return;
    case "default":
      await httpClient.put(base + "/default", { category_id: change.id });
      return;
    case "delete":
      await httpClient.delete(base + "/" + encodeURIComponent(change.id));
  }
}
