import {
  STOCK_SERIAL_MAX_OFFSET,
  STOCK_SERIAL_PAGE_SIZE,
  STOCK_SERIAL_PAGE_SIZES,
} from "./stock-serial.constants.ts";
import type {
  StockSerialsListParams,
  StockSerialsPageParams,
} from "./stock-serial.types.ts";

export function parseStockSerialsParams(
  query: Record<string, unknown>,
): StockSerialsPageParams {
  const rawLimit = typeof query.limit === "string" ? Number(query.limit) : NaN;
  const limit =
    STOCK_SERIAL_PAGE_SIZES.find((value) => value === rawLimit) ??
    STOCK_SERIAL_PAGE_SIZE;
  const rawPage = typeof query.page === "string" ? Number(query.page) : NaN;
  const maxPage = Math.floor(STOCK_SERIAL_MAX_OFFSET / limit) + 1;
  return {
    search: typeof query.search === "string" ? query.search.trim() : "",
    page: Number.isFinite(rawPage)
      ? Math.min(maxPage, Math.max(1, Math.floor(rawPage)))
      : 1,
    limit,
  };
}

export function stockSerialsListParams(
  params: StockSerialsPageParams,
): StockSerialsListParams {
  return {
    search: params.search,
    offset: (params.page - 1) * params.limit,
    limit: params.limit,
  };
}

export function stockSerialsUrlParams(
  params: StockSerialsPageParams,
): Record<string, string | undefined> {
  return {
    search: params.search || undefined,
    page: params.page === 1 ? undefined : String(params.page),
    limit:
      params.limit === STOCK_SERIAL_PAGE_SIZE
        ? undefined
        : String(params.limit),
  };
}
