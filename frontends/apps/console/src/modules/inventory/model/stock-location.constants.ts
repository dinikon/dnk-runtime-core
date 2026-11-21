import type { StockLocationType } from "./stock-location.types.ts";
export const STOCK_LOCATION_TYPES = [
  "STORAGE",
  "RECEIVING",
  "SHIPPING",
  "QUARANTINE",
  "TRANSIT",
] as const;
export const STOCK_LOCATION_TYPE_LABELS: Readonly<
  Record<StockLocationType, string>
> = {
  STORAGE: "Хранение",
  RECEIVING: "Приёмка",
  SHIPPING: "Отгрузка",
  QUARANTINE: "Карантин",
  TRANSIT: "Транзит",
};
export const STOCK_LOCATION_PAGE_SIZE = 50;
export const STOCK_LOCATION_PAGE_SIZES = [20, 50, 100] as const;
export const STOCK_LOCATION_MAX_OFFSET = 2_147_483_647;
export const STOCK_LOCATION_SEARCH_DELAY = 300;
export function isStockLocationType(
  value: unknown,
): value is StockLocationType {
  return STOCK_LOCATION_TYPES.some((type) => type === value);
}
