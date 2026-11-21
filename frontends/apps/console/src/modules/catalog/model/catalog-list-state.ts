import type { ProductStatus } from "./product.types";

export const CATALOG_PAGE_SIZE = 20;
const MAX_PAGE = Math.floor(2147483600 / CATALOG_PAGE_SIZE) + 1;

export interface CatalogItemsParams {
  search: string;
  status: ProductStatus | undefined;
  page: number;
}

export function catalogPage(value: unknown): number {
  const page =
    typeof value === "string" || typeof value === "number"
      ? Number(value)
      : NaN;
  return Number.isFinite(page)
    ? Math.min(MAX_PAGE, Math.max(1, Math.floor(page)))
    : 1;
}

export function parseCatalogItemsParams(
  query: Record<string, unknown>,
): CatalogItemsParams {
  return {
    search: typeof query.search === "string" ? query.search : "",
    status:
      query.status === "draft" ||
      query.status === "active" ||
      query.status === "archived"
        ? query.status
        : undefined,
    page: catalogPage(query.page),
  };
}
