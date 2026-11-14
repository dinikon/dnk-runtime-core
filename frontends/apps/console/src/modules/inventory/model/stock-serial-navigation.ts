import type { RouteLocationRaw } from "vue-router";
export function stockSerialsLocation(
  itemId: string,
  returnTo: string,
): RouteLocationRaw {
  return {
    name: "inventory-stock-serials",
    params: { inventoryItemId: itemId },
    query: { returnTo },
  };
}
export function stockSerialLocation(
  itemId: string,
  serialId: string,
  returnTo: string,
): RouteLocationRaw {
  return {
    name: "inventory-stock-serial",
    params: { inventoryItemId: itemId, serialId },
    query: { returnTo },
  };
}
export function stockSerialsReturnPath(
  itemId: string,
  value: unknown,
  detail = false,
): string {
  const fallback = `/inventory/items/${encodeURIComponent(itemId)}${detail ? "/serials" : ""}`;
  return typeof value === "string" &&
    !/[\\\u0000-\u001f]/.test(value) &&
    value.split(/[?#]/, 1)[0] === fallback
    ? value
    : fallback;
}
