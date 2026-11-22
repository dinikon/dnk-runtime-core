import type { ProductPatch } from "./product.types";
import type { ProductSection } from "./product.types";
import { convertMeasurement } from "./measurement-conversion.ts";

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
  patch: ProductPatch,
  allowInheritedTitle = false,
): string {
  if (section === "content" && patch.content) {
    const name = patch.content.values.title ?? "";
    if (
      (!allowInheritedTitle || patch.content.values.title !== undefined) &&
      (!name.trim() || name.length > 255)
    )
      return "Введите название до 255 символов.";
  }
  if (section === "sku" && patch.sku && patch.sku.length > 128)
    return "SKU не длиннее 128 символов.";
  if (patch.purchase_price != null) {
    const purchase = decimal(patch.purchase_price);
    if (purchase === null || purchase < 0n)
      return "Укажите неотрицательную закупочную цену с точностью до 6 знаков.";
  }
  if (section === "price" && patch.price_specification) {
    const price = patch.price_specification;
    const regular = decimal(price.regular_price),
      sale = price.sale_price === null ? null : decimal(price.sale_price);
    if (regular === null || regular < 0n)
      return "Укажите неотрицательную цену с точностью до 6 знаков.";
    if (price.sale_price !== null && (sale === null || sale < 0n))
      return "Укажите неотрицательную акционную цену с точностью до 6 знаков.";
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
  return "";
}

export const fieldSections: Record<string, ProductSection> = {
  status: "status",
  sku: "sku",
  virtual: "virtual",
  purchase_price: "purchase_price",
  price_specification: "price",
  stock: "stock",
  weight: "measurements",
  dimensions: "measurements",
  content: "content",
  gallery: "galleries",
};
