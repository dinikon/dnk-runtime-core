import type { UpdateItemRequest } from "../api/catalog.dto";
import type { ProductSection } from "./product.types";
import { convertMeasurement } from "./measurement-conversion";

/** Возвращает точный Decimal в миллионных долях, без преобразования суммы в Number. */
function decimal(value: string): bigint | null {
  if (value.length > 1000) return null;
  const normalized = convertMeasurement(value, "g", "g");
  if (normalized === null || !/^-?\d+(?:\.\d{1,6})?$/.test(normalized))
    return null;
  const [whole, fraction = ""] = normalized.replace(/^-/, "").split(".");
  const result = BigInt(whole!) * 1000000n + BigInt(fraction.padEnd(6, "0"));
  return normalized.startsWith("-") ? -result : result;
}

/** Проверяет готовность раздела к отправке; бизнес-инварианты повторно проверяет сервер. */
export function sectionError(
  section: ProductSection,
  patch: UpdateItemRequest,
): string {
  if (section === "content" && patch.content) {
    const name = patch.content.values.name ?? "";
    if (!name.trim() || name.length > 255)
      return "Введите название до 255 символов.";
  }
  if (section === "sku" && patch.sku && patch.sku.length > 128)
    return "SKU не длиннее 128 символов.";
  if (section === "price" && patch.price_specification) {
    const price = patch.price_specification;
    const regular = decimal(price.regular_price),
      sale = price.sale_price === null ? null : decimal(price.sale_price);
    if (regular === null || regular < 0n || !/^[A-Z]{3}$/.test(price.currency))
      return "Укажите неотрицательную цену до 6 знаков и код валюты.";
    if (
      price.sale_price !== null &&
      (sale === null || sale < 0n || sale > regular)
    )
      return "Цена скидки должна быть от 0 до обычной цены.";
    if (
      price.sale_price === null &&
      (price.date_on_sale_from || price.date_on_sale_to)
    )
      return "Для периода акции укажите цену скидки.";
    if (
      price.date_on_sale_from &&
      price.date_on_sale_to &&
      price.date_on_sale_from > price.date_on_sale_to
    )
      return "Начало акции должно быть раньше окончания.";
  }
  if (
    section === "stock" &&
    patch.stock?.manage_stock &&
    !Number.isSafeInteger(patch.stock.stock_quantity)
  )
    return "Введите целое количество.";
  if (section === "measurements") {
    const measurements = [
      patch.weight,
      ...Object.values(patch.dimensions ?? {}),
    ];
    for (const value of measurements) {
      if (!value) continue;
      const base = convertMeasurement(value.value, value.unit, "g");
      if (base === null || decimal(base) === null || decimal(base)! < 0n)
        return "Введите неотрицательные измерения с точностью до 6 знаков в базовой единице.";
    }
  }
  if (
    section === "attributes" &&
    patch.attributes?.some((value) => !value.option_ids.length)
  )
    return "Выберите хотя бы одно значение характеристики.";
  if (section === "metadata" && patch.metadata) {
    const keys = new Set<string>();
    for (const entry of patch.metadata) {
      if (
        !/^[a-zA-Z][a-zA-Z0-9_.-]{0,63}$/.test(entry.key) ||
        keys.has(entry.key)
      )
        return "Укажите уникальные корректные ключи metadata.";
      keys.add(entry.key);
      if (
        entry.value_type === "decimal" &&
        (typeof entry.value !== "string" || decimal(entry.value) === null)
      )
        return "Введите число metadata до 6 знаков после запятой.";
    }
  }
  if (
    section === "categories" &&
    patch.category_ids?.length &&
    (!patch.primary_category_id ||
      !patch.category_ids.includes(patch.primary_category_id))
  )
    return "Выберите основную категорию.";
  return "";
}

export const fieldSections: Record<string, ProductSection> = {
  status: "status",
  sku: "sku",
  virtual: "virtual",
  price_specification: "price",
  stock: "stock",
  weight: "measurements",
  dimensions: "measurements",
  content: "content",
  gallery: "galleries",
  attributes: "attributes",
  metadata: "metadata",
  category_ids: "categories",
  primary_category_id: "categories",
  tag_ids: "tags",
};
