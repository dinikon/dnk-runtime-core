export function parsePage(value: unknown): number {
  if (typeof value !== "string" || !/^[1-9]\d*$/.test(value)) return 1;
  const page = Number(value);
  return Number.isSafeInteger(page) && page <= 1_000_000 ? page : 1;
}
export function parseStockStatus(value: unknown): string {
  return typeof value === "string" &&
    ["in_stock", "out_of_stock", "on_backorder", "unknown"].includes(value)
    ? value
    : "";
}
