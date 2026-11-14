import type { RouteLocationRaw } from "vue-router";
export function stockLotsLocation(
  itemId: string,
  returnTo: string,
): RouteLocationRaw {
  return {
    name: "inventory-stock-lots",
    params: { inventoryItemId: itemId },
    query: { returnTo },
  };
}
export function stockLotLocation(
  itemId: string,
  lotId: string,
  returnTo: string,
): RouteLocationRaw {
  return {
    name: "inventory-stock-lot",
    params: { inventoryItemId: itemId, lotId },
    query: { returnTo },
  };
}
export function stockLotsReturnPath(
  itemId: string,
  value: unknown,
  detail = false,
): string {
  const fallback = `/inventory/items/${encodeURIComponent(itemId)}${detail ? "/lots" : ""}`;
  return typeof value === "string" &&
    !/[\\\u0000-\u001f]/.test(value) &&
    value.split(/[?#]/, 1)[0] === fallback
    ? value
    : fallback;
}
