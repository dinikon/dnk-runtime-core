import {
  STOCK_LOCATION_MAX_OFFSET,
  STOCK_LOCATION_PAGE_SIZE,
  STOCK_LOCATION_PAGE_SIZES,
  isStockLocationType,
} from "./stock-location.constants.ts";
import type {
  StockLocationsPageParams,
  StockLocationsListParams,
} from "./stock-location.types.ts";
export function parseStockLocationsParams(
  query: Record<string, unknown>,
): StockLocationsPageParams {
  const rawLimit = typeof query.limit === "string" ? Number(query.limit) : NaN;
  const limit =
    STOCK_LOCATION_PAGE_SIZES.find((value) => value === rawLimit) ??
    STOCK_LOCATION_PAGE_SIZE;
  const rawPage = typeof query.page === "string" ? Number(query.page) : NaN;
  const maxPage = Math.floor(STOCK_LOCATION_MAX_OFFSET / limit) + 1;
  const parent =
    typeof query.parent_location_id === "string" &&
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
      query.parent_location_id,
    )
      ? query.parent_location_id.toLowerCase()
      : null;
  return {
    search: typeof query.search === "string" ? query.search.trim() : "",
    activity:
      query.is_active === "true"
        ? "active"
        : query.is_active === "false"
          ? "inactive"
          : "all",
    locationType: isStockLocationType(query.location_type)
      ? query.location_type
      : null,
    parentLocationId: parent,
    page: Number.isFinite(rawPage)
      ? Math.min(maxPage, Math.max(1, Math.floor(rawPage)))
      : 1,
    limit,
  };
}
export function stockLocationsListParams(
  params: StockLocationsPageParams,
): StockLocationsListParams {
  return {
    search: params.search,
    isActive: params.activity === "all" ? null : params.activity === "active",
    locationType: params.locationType,
    parentLocationId: params.parentLocationId,
    offset: (params.page - 1) * params.limit,
    limit: params.limit,
  };
}
export function stockLocationsUrlParams(
  params: StockLocationsPageParams,
): Record<string, string | undefined> {
  return {
    search: params.search || undefined,
    is_active:
      params.activity === "all"
        ? undefined
        : String(params.activity === "active"),
    location_type: params.locationType ?? undefined,
    parent_location_id: params.parentLocationId ?? undefined,
    page: params.page === 1 ? undefined : String(params.page),
    limit:
      params.limit === STOCK_LOCATION_PAGE_SIZE
        ? undefined
        : String(params.limit),
  };
}
