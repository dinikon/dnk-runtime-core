import {
  PACKAGING_TYPE_MAX_OFFSET,
  PACKAGING_TYPE_PAGE_SIZE,
  PACKAGING_TYPE_PAGE_SIZES,
} from "./packaging-type.constants.ts";
import type {
  PackagingTypesListParams,
  PackagingTypesPageParams,
} from "./packaging-type.types.ts";

export function parsePackagingTypesParams(
  query: Record<string, unknown>,
): PackagingTypesPageParams {
  const rawLimit = typeof query.limit === "string" ? Number(query.limit) : NaN;
  const limit =
    PACKAGING_TYPE_PAGE_SIZES.find((value) => value === rawLimit) ??
    PACKAGING_TYPE_PAGE_SIZE;
  const rawPage = typeof query.page === "string" ? Number(query.page) : NaN;
  const maxPage = Math.floor(PACKAGING_TYPE_MAX_OFFSET / limit) + 1;
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

export function packagingTypesListParams(
  params: PackagingTypesPageParams,
): PackagingTypesListParams {
  return {
    search: params.search,
    isActive: params.activity === "all" ? null : params.activity === "active",
    offset: (params.page - 1) * params.limit,
    limit: params.limit,
  };
}

export function packagingTypesUrlParams(
  params: PackagingTypesPageParams,
): Record<string, string | undefined> {
  return {
    search: params.search || undefined,
    is_active:
      params.activity === "all"
        ? undefined
        : String(params.activity === "active"),
    page: params.page === 1 ? undefined : String(params.page),
    limit:
      params.limit === PACKAGING_TYPE_PAGE_SIZE
        ? undefined
        : String(params.limit),
  };
}
