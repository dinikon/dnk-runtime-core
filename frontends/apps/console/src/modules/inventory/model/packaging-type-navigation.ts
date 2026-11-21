import type { RouteLocationRaw } from "vue-router";
export function packagingTypeEditLocation(
  packagingTypeId: string,
  returnTo: string,
): RouteLocationRaw {
  return {
    name: "inventory-packaging-type-edit",
    params: { packagingTypeId },
    query: { returnTo },
  };
}
export function packagingTypeReturnPath(value: unknown): string {
  return typeof value === "string" &&
    /^\/inventory\/packaging-types(?:\?|#|$)/.test(value) &&
    !/[\\\u0000-\u001f]/.test(value)
    ? value
    : "/inventory/packaging-types";
}
