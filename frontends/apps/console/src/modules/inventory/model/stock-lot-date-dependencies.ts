import type { QueryClient } from "@tanstack/vue-query";
import type { InventoryScope } from "./inventory-scope.types.ts";
export interface StockLotDateDependency {
  inventoryItemId: string;
  lotId?: string;
}
export interface StockLotDateQuery {
  queryKey: readonly unknown[];
  meta?: Record<string, unknown>;
}
export function stockLotDateDependency(
  inventoryItemId: string,
  lotId?: string,
): { inventoryStockLotDates: StockLotDateDependency } {
  return { inventoryStockLotDates: { inventoryItemId, lotId } };
}
export function isStockLotDateView(
  query: StockLotDateQuery,
  scope: InventoryScope,
  itemId: string,
  lotId: string,
): boolean {
  const key = query.queryKey;
  if (
    key[0] !== "inventory" ||
    !scope.every((part, index) => part === key[index + 1])
  )
    return false;
  // Списки партий обновляются явно; сохранённая карточка уже получена из PATCH.
  if (key[4] === "lots" && key[5] === itemId)
    return key[6] === "list" || key[6] === "candidates";
  const dependency = query.meta?.inventoryStockLotDates;
  return (
    typeof dependency === "object" &&
    dependency !== null &&
    "inventoryItemId" in dependency &&
    dependency.inventoryItemId === itemId &&
    (!("lotId" in dependency) ||
      dependency.lotId === undefined ||
      dependency.lotId === lotId)
  );
}
export async function invalidateStockLotDateViews(
  cache: QueryClient,
  scope: InventoryScope,
  itemId: string,
  lotId: string,
): Promise<void> {
  await cache.invalidateQueries({
    predicate: (query) => isStockLotDateView(query, scope, itemId, lotId),
  });
}
