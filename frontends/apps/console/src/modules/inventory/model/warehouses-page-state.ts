import {
  WAREHOUSE_MAX_OFFSET,
  WAREHOUSE_PAGE_SIZE,
  WAREHOUSE_PAGE_SIZES,
} from "./warehouse.constants.ts";
import type {
  WarehousesListParams,
  WarehousesPageParams,
} from "./warehouse.types.ts";

export function parseWarehousesParams(
  query: Record<string, unknown>,
): WarehousesPageParams {
  const rawLimit = typeof query.limit === "string" ? Number(query.limit) : NaN;
  const limit =
    WAREHOUSE_PAGE_SIZES.find((value) => value === rawLimit) ??
    WAREHOUSE_PAGE_SIZE;
  const rawPage = typeof query.page === "string" ? Number(query.page) : NaN;
  const maxPage = Math.floor(WAREHOUSE_MAX_OFFSET / limit) + 1;
  return {
    activity:
      query.is_active === "true"
        ? "active"
        : query.is_active === "false"
          ? "inactive"
          : "all",
    search: typeof query.search === "string" ? query.search.trim() : "",
    page: Number.isFinite(rawPage)
      ? Math.min(maxPage, Math.max(1, Math.floor(rawPage)))
      : 1,
    limit,
  };
}

export function warehousesListParams(
  params: WarehousesPageParams,
): WarehousesListParams {
  return {
    search: params.search,
    isActive: params.activity === "all" ? null : params.activity === "active",
    offset: (params.page - 1) * params.limit,
    limit: params.limit,
  };
}

export function warehousesUrlParams(
  params: WarehousesPageParams,
): Record<string, string | undefined> {
  return {
    search: params.search || undefined,
    is_active:
      params.activity === "all"
        ? undefined
        : String(params.activity === "active"),
    page: params.page === 1 ? undefined : String(params.page),
    limit:
      params.limit === WAREHOUSE_PAGE_SIZE ? undefined : String(params.limit),
  };
}
