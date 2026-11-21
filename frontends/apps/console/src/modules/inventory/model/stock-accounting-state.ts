import type {
  StockReadParams,
  StockFilters,
  StockReadKind,
} from "./stock-accounting.types.ts";
import { stockFilterKeys } from "./stock-accounting-navigation.ts";
export function readStockAccountingQuery(
  query: Record<string, unknown>,
  kind: StockReadKind,
): { params: StockReadParams; error: string } {
  const filters: StockFilters = {};
  let error = "";
  for (const key of Object.keys(stockFilterKeys) as (keyof StockFilters)[]) {
    const raw = query[stockFilterKeys[key]];
    if (typeof raw !== "string" || !raw) continue;
    if (key === "includeZero") {
      if (kind === "positions") filters.includeZero = raw === "true";
      continue;
    }
    filters[key] = raw;
    if (
      key.endsWith("Id") &&
      !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
        raw,
      )
    )
      error = "Некорректная ссылка в фильтре.";
  }
  if (kind === "positions")
    for (const key of [
      "documentId",
      "executionId",
      "postingId",
      "operationType",
      "postedFrom",
      "postedTo",
    ] as const)
      delete filters[key];
  if (
    filters.postedFrom &&
    filters.postedTo &&
    (Date.parse(filters.postedFrom) > Date.parse(filters.postedTo) ||
      filters.postedFrom === filters.postedTo)
  )
    error = "Начало периода должно быть раньше окончания.";
  const offset =
    typeof query.offset === "string" && /^\d+$/.test(query.offset)
      ? Number(query.offset)
      : 0;
  return {
    params: {
      filters,
      offset: Number.isSafeInteger(offset) ? offset : 0,
      limit: 20,
    },
    error,
  };
}
export function changeStockFilters(
  filters: StockFilters,
  patch: Partial<StockFilters>,
): StockFilters {
  const result = { ...filters, ...patch };
  if ("warehouseId" in patch && patch.warehouseId !== filters.warehouseId)
    delete result.locationId;
  if (
    "inventoryItemId" in patch &&
    patch.inventoryItemId !== filters.inventoryItemId
  ) {
    delete result.lotId;
    delete result.serialId;
  }
  if ("lotId" in patch && patch.lotId !== filters.lotId) delete result.serialId;
  return result;
}

export function readTrackingColumns(
  value: unknown,
): import("./stock-accounting.types").StockTrackingColumns {
  const names = typeof value === "string" ? value.split(",") : [];
  return { lot: names.includes("lot"), serial: names.includes("serial") };
}
export function trackingColumnsQuery(
  value: import("./stock-accounting.types").StockTrackingColumns,
): string | undefined {
  return (
    [value.lot ? "lot" : "", value.serial ? "serial" : ""]
      .filter(Boolean)
      .join(",") || undefined
  );
}

export function stockAccountingPageOffset(
  offset: number,
  total: number,
  limit = 20,
): number {
  return total <= 0
    ? 0
    : offset < total
      ? offset
      : Math.floor((total - 1) / limit) * limit;
}
