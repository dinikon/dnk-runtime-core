import type { RouteLocationRaw } from "vue-router";
export function stockLocationRouteId(value: unknown): string {
  return typeof value === "string" ? value.toLowerCase() : "";
}
export function stockLocationsLocation(
  warehouseId: string,
  returnTo: string,
): RouteLocationRaw {
  return {
    name: "inventory-stock-locations",
    params: { warehouseId },
    query: { returnTo },
  };
}
export function stockLocationEditLocation(
  warehouseId: string,
  locationId: string,
  returnTo: string,
): RouteLocationRaw {
  return {
    name: "inventory-stock-location-edit",
    params: { warehouseId, locationId },
    query: { returnTo },
  };
}
function allowedPath(
  value: unknown,
  paths: readonly string[],
  fallback: string,
): string {
  if (
    typeof value !== "string" ||
    !value.startsWith("/") ||
    value.startsWith("//") ||
    /[\\\u0000-\u001f]/.test(value)
  )
    return fallback;
  try {
    const url = new URL(value, "https://console.invalid");
    return url.origin === "https://console.invalid" &&
      paths.includes(url.pathname)
      ? value
      : fallback;
  } catch {
    return fallback;
  }
}
export function stockLocationsReturnPath(
  warehouseId: string,
  value: unknown,
): string {
  const path = `/inventory/warehouses/${encodeURIComponent(warehouseId)}/locations`;
  return allowedPath(value, [path], path);
}
export function warehouseLocationsReturnPath(
  warehouseId: string,
  value: unknown,
): string {
  const path = `/inventory/warehouses/${encodeURIComponent(warehouseId)}`;
  return allowedPath(value, ["/inventory/warehouses", path], path);
}
