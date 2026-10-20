import type { QueryClient } from "@tanstack/vue-query";
export function catalogItemLocation(
  id: string,
  locale: string,
): { path: string; query: { locale: string } } {
  return {
    path: `/catalog/items/${encodeURIComponent(id)}/edit`,
    query: { locale },
  };
}
export async function invalidateCatalogItems(
  cache: QueryClient,
  tenantId: string,
): Promise<void> {
  await cache.invalidateQueries({ queryKey: ["catalog", tenantId] });
}
