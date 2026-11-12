import type { RouteLocationRaw } from "vue-router";

export function inventoryItemEditLocation(
  inventoryItemId: string,
  returnTo: string,
): RouteLocationRaw {
  return {
    name: "inventory-item-edit",
    params: { inventoryItemId },
    query: { returnTo },
  };
}

export function inventoryItemReturnPath(value: unknown): string {
  // Allow only this slice's local origin screens; never navigate to arbitrary URLs.
  return typeof value === "string" &&
    /^\/(?:inventory\/items|catalog\/items)(?:\?|#|\/|$)/.test(value) &&
    !/[\\\u0000-\u001f]/.test(value)
    ? value
    : "/inventory/items";
}
