import type { CatalogListItem } from "./catalog.types";

function normalizedDecimal(value: string): string {
  return value.includes(".")
    ? value.replace(/0+$/, "").replace(/\.$/, "")
    : value;
}

/** Форматирует точные строки API, не преобразуя денежные значения в Number. */
export function catalogListPrice(item: CatalogListItem): string {
  if (item.kind === "variable") {
    if (item.mixed_currencies) return "Разные валюты";
    if (item.min_price == null) return "Цена вариантов не задана";
    const range =
      item.max_price != null &&
      normalizedDecimal(item.max_price) !== normalizedDecimal(item.min_price)
        ? `${normalizedDecimal(item.min_price)}–${normalizedDecimal(item.max_price)}`
        : normalizedDecimal(item.min_price);
    return `${range} ${item.currency ?? ""}`.trim();
  }
  return item.price == null
    ? "Цена не задана"
    : `${normalizedDecimal(item.price)} ${item.currency ?? ""}`.trim();
}
