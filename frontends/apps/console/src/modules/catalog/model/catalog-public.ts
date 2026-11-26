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
    kind: item.virtual ? "service" : "product",
    sku: item.sku ?? null,
  };
}

export interface CatalogPreviewChoice {
  id: string;
  title: string;
  sku: string | null;
  kind: "simple" | "variable" | "variant";
}
export interface CatalogPreviewPage {
  items: CatalogPreviewChoice[];
  total: number;
}
export async function searchCatalogPreviewProducts(
  locale: string,
  search: string,
  offset: number,
  signal: AbortSignal,
): Promise<CatalogPreviewPage> {
  const { catalogApi } = await import("../api/catalog.api");
  const page = await catalogApi.listItems(
    locale,
    search,
    offset,
    20,
    undefined,
    signal,
  );
  return {
    total: page.total,
    items: page.items
      .filter((i) => i.kind !== "variant")
      .map((i) => ({
        id: i.id,
        title: i.title ?? i.sku ?? i.id,
        sku: i.sku ?? null,
        kind: i.kind ?? "simple",
      })),
  };
}
export async function searchCatalogPreviewVariants(
  rootId: string,
  locale: string,
  offset: number,
  signal: AbortSignal,
): Promise<CatalogPreviewPage> {
  const { catalogApi } = await import("../api/catalog.api");
  const page = await catalogApi.listVariants(
    rootId,
    locale,
    offset,
    20,
    signal,
  );
  return {
    total: page.total,
    items: page.items.map((i) => ({
      id: i.id,
      title: i.title ?? i.sku ?? i.id,
      sku: i.sku ?? null,
      kind: i.kind ?? "variant",
    })),
  };
}

export interface CatalogPublicationChoice {
  id: string;
  title: string;
  sku: string | null;
  kind: "simple" | "variable" | "variant";
  available: boolean;
}
export interface CatalogPublicationPage {
  items: CatalogPublicationChoice[];
  total: number;
}
export async function searchCatalogPublicationProducts(
  locale: string,
  search: string,
  offset: number,
  signal: AbortSignal,
): Promise<CatalogPublicationPage> {
  const { catalogApi } = await import("../api/catalog.api");
  const page = await catalogApi.listItems(
    locale,
    search,
    offset,
    20,
    undefined,
    signal,
  );
  return {
    total: page.total,
    items: page.items.map((i) => ({
      id: i.id,
      title: i.title ?? i.sku ?? i.id,
      sku: i.sku,
      kind: i.kind ?? "simple",
      available: i.status !== "archived",
    })),
  };
}
export async function searchCatalogPublicationVariants(
  rootId: string,
  locale: string,
  offset: number,
  signal: AbortSignal,
): Promise<CatalogPublicationPage> {
  const { catalogApi } = await import("../api/catalog.api");
  const page = await catalogApi.listVariants(
    rootId,
    locale,
    offset,
    20,
    signal,
  );
  return {
    total: page.total,
    items: page.items.map((i) => ({
      id: i.id,
      title: i.title ?? i.sku ?? i.id,
      sku: i.sku,
      kind: i.kind ?? "variant",
      available: i.status !== "archived",
    })),
  };
}

export async function listCatalogLocales(
  signal: AbortSignal,
): Promise<{ code: string; name: string }[]> {
  const { catalogApi } = await import("../api/catalog.api");
  return catalogApi.locales(signal);
}
