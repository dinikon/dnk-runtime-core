import {
  INVENTORY_MAX_OFFSET,
  INVENTORY_PAGE_SIZE,
  INVENTORY_PAGE_SIZES,
} from "./inventory-item.constants.ts";
import type {
  InventoryItemsListParams,
  InventoryItemsPageParams,
} from "./inventory-item.types.ts";

export function parseInventoryItemsParams(
  query: Record<string, unknown>,
): InventoryItemsPageParams {
  const rawLimit = typeof query.limit === "string" ? Number(query.limit) : NaN;
  const limit =
    INVENTORY_PAGE_SIZES.find((value) => value === rawLimit) ??
    INVENTORY_PAGE_SIZE;
  const rawPage = typeof query.page === "string" ? Number(query.page) : NaN;
  const maxPage = Math.floor(INVENTORY_MAX_OFFSET / limit) + 1;
  return {
    search: typeof query.search === "string" ? query.search.trim() : "",
    page: Number.isFinite(rawPage)
      ? Math.min(maxPage, Math.max(1, Math.floor(rawPage)))
      : 1,
    limit,
  };
}

export function inventoryItemsListParams(
  params: InventoryItemsPageParams,
): InventoryItemsListParams {
  return {
    search: params.search,
    offset: (params.page - 1) * params.limit,
    limit: params.limit,
  };
}

export function inventoryItemsUrlParams(
  params: InventoryItemsPageParams,
): Record<string, string | undefined> {
  return {
    search: params.search || undefined,
    page: params.page === 1 ? undefined : String(params.page),
    limit:
      params.limit === INVENTORY_PAGE_SIZE ? undefined : String(params.limit),
  };
}
