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

export interface SalesCatalogChoice {
  id: string;
  title: string;
  price: string | null;
  currency: string | null;
  kind: "product" | "service";
  sku: string | null;
}
export async function searchSalesCatalog(
  search: string,
  signal?: AbortSignal,
): Promise<SalesCatalogChoice[]> {
  const { catalogApi } = await import("../api/catalog.api");
  const page = await catalogApi.listItems(
    "uk",
    search,
    0,
    20,
    undefined,
    signal,
  );
  return page.items
    .filter((i) => i.kind !== "variable")
    .map((i) => ({
      id: i.id,
      title: i.title ?? "",
      price: i.price ?? null,
      currency: i.currency ?? null,
      kind: "product",
      sku: i.sku ?? null,
    }));
}
export async function readSalesCatalog(
  id: string,
): Promise<SalesCatalogChoice> {
  const { catalogApi } = await import("../api/catalog.api");
  const item = await catalogApi.getItem(id, "uk");
  if (item.kind === "variable")
    throw new Error("Контейнер не является продаваемой позицией.");
  return {
    id: item.id,
    title: item.title ?? "",
    price: item.price ?? null,
    currency: item.price_specification?.currency ?? null,
    kind: item.virtual ? "service" : "product",
    sku: item.sku ?? null,
  };
}
