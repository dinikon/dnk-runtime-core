import {
  STOCK_LOT_MAX_OFFSET,
  STOCK_LOT_PAGE_SIZE,
  STOCK_LOT_PAGE_SIZES,
} from "./stock-lot.constants.ts";
import type {
  StockLotsListParams,
  StockLotsPageParams,
} from "./stock-lot.types.ts";

export function parseStockLotsParams(
  query: Record<string, unknown>,
): StockLotsPageParams {
  const rawLimit = typeof query.limit === "string" ? Number(query.limit) : NaN;
  const limit =
    STOCK_LOT_PAGE_SIZES.find((value) => value === rawLimit) ??
    STOCK_LOT_PAGE_SIZE;
  const rawPage = typeof query.page === "string" ? Number(query.page) : NaN;
  const maxPage = Math.floor(STOCK_LOT_MAX_OFFSET / limit) + 1;
  return {
    search: typeof query.search === "string" ? query.search.trim() : "",
    page: Number.isFinite(rawPage)
      ? Math.min(maxPage, Math.max(1, Math.floor(rawPage)))
      : 1,
    limit,
  };
}

export function stockLotsListParams(
  params: StockLotsPageParams,
): StockLotsListParams {
  return {
    search: params.search,
    offset: (params.page - 1) * params.limit,
    limit: params.limit,
  };
}

export function stockLotsUrlParams(
  params: StockLotsPageParams,
): Record<string, string | undefined> {
  return {
    search: params.search || undefined,
    page: params.page === 1 ? undefined : String(params.page),
    limit:
      params.limit === STOCK_LOT_PAGE_SIZE ? undefined : String(params.limit),
  };
}
