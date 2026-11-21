import {
  ITEM_PACKAGING_MAX_OFFSET,
  ITEM_PACKAGING_PAGE_SIZE,
  ITEM_PACKAGING_PAGE_SIZES,
} from "./item-packaging.constants.ts";
import type {
  ItemPackagingsListParams,
  ItemPackagingsPageParams,
} from "./item-packaging.types.ts";

export function parseItemPackagingsParams(
  query: Record<string, unknown>,
): ItemPackagingsPageParams {
  const rawLimit = typeof query.limit === "string" ? Number(query.limit) : NaN;
  const limit =
    ITEM_PACKAGING_PAGE_SIZES.find((value) => value === rawLimit) ??
    ITEM_PACKAGING_PAGE_SIZE;
  const rawPage = typeof query.page === "string" ? Number(query.page) : NaN;
  const maxPage = Math.floor(ITEM_PACKAGING_MAX_OFFSET / limit) + 1;
  return {
    search: typeof query.search === "string" ? query.search.trim() : "",
    page: Number.isFinite(rawPage)
      ? Math.min(maxPage, Math.max(1, Math.floor(rawPage)))
      : 1,
    limit,
  };
}

export function itemPackagingsListParams(
  params: ItemPackagingsPageParams,
): ItemPackagingsListParams {
  return {
    search: params.search,
    offset: (params.page - 1) * params.limit,
    limit: params.limit,
  };
}

export function itemPackagingsUrlParams(
  params: ItemPackagingsPageParams,
): Record<string, string | undefined> {
  return {
    search: params.search || undefined,
    page: params.page === 1 ? undefined : String(params.page),
    limit:
      params.limit === ITEM_PACKAGING_PAGE_SIZE
        ? undefined
        : String(params.limit),
  };
}
