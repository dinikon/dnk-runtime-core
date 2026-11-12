import type { RouteLocationRaw } from "vue-router";
export function warehouseEditLocation(
  warehouseId: string,
  returnTo: string,
): RouteLocationRaw {
  return {
    name: "inventory-warehouse-edit",
    params: { warehouseId },
    query: { returnTo },
  };
}
export function warehouseReturnPath(value: unknown): string {
  return typeof value === "string" &&
    /^\/inventory\/warehouses(?:\?|#|$)/.test(value) &&
    !/[\\\u0000-\u001f]/.test(value)
    ? value
    : "/inventory/warehouses";
}
