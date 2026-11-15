import type { StockFilters, StockReadKind } from "./stock-accounting.types.ts";
export interface StockAccountingTarget {
  kind:
    | "position"
    | "document"
    | "execution"
    | "posting"
    | "item"
    | "warehouse"
    | "lot"
    | "serial";
  id: string;
  itemId?: string;
  operationType?: string;
}
export function accountingTarget(target: StockAccountingTarget): {
  name: string;
  params: Record<string, string>;
} {
  const names = {
    position: "inventory-stock-position",
    document:
      target.operationType === "ISSUE"
        ? "inventory-issue-document"
        : "inventory-receipt-document",
    execution: "inventory-stock-execution",
    posting: "inventory-stock-posting",
    item: "inventory-item-edit",
    warehouse: "inventory-warehouse-edit",
    lot: "inventory-stock-lot",
    serial: "inventory-stock-serial",
  };
  const param = {
    position: "positionId",
    document: "documentId",
    execution: "identifier",
    posting: "identifier",
    item: "inventoryItemId",
    warehouse: "warehouseId",
    lot: "lotId",
    serial: "serialId",
  };
  return {
    name: names[target.kind],
    params: {
      [param[target.kind]]: target.id,
      ...(target.itemId ? { inventoryItemId: target.itemId } : {}),
    },
  };
}
export const stockFilterNames = {
  warehouseId: "Склад",
  locationId: "Локация",
  ownerId: "Владелец",
  inventoryItemId: "SKU",
  lotId: "Партия",
  serialId: "Серийный экземпляр",
} as const;
export const stockFilterKeys = {
  warehouseId: "warehouse_id",
  locationId: "location_id",
  ownerId: "owner_id",
  inventoryItemId: "inventory_item_id",
  lotId: "lot_id",
  serialId: "serial_id",
  positionId: "position_id",
  documentId: "document_id",
  executionId: "execution_id",
  postingId: "posting_id",
  stockStatus: "stock_status",
  operationType: "operation_type",
  postedFrom: "posted_from",
  postedTo: "posted_to",
  search: "search",
  includeZero: "include_zero",
} as const;
export function stockReadLocation(
  kind: StockReadKind,
  filters: StockFilters,
): { name: string; query: Record<string, string> } {
  const query: Record<string, string> = {};
  for (const key of Object.keys(stockFilterKeys) as (keyof StockFilters)[]) {
    const value = filters[key];
    if (value !== undefined && value !== "")
      query[stockFilterKeys[key]] = String(value);
  }
  return { name: `inventory-stock-${kind}`, query };
}
