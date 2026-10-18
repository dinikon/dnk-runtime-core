import DOMPurify from "dompurify";
import type { CatalogItem } from "./catalog.types";
import type { ProductOverviewModel } from "./product.types";
export const statusLabels: Record<string, string> = {
  draft: "Черновик",
  active: "Активный",
  archived: "В архиве",
};
export const stockLabels: Record<string, string> = {
  in_stock: "В наличии",
  out_of_stock: "Нет в наличии",
  on_backorder: "Предзаказ",
};
export const sectionTitles: Record<string, string> = {
  content: "Тексты товара",
  status: "Статус",
  sku: "Артикул",
  virtual: "Виртуальный товар",
  price: "Цена",
  stock: "Наличие",
  measurements: "Вес и размеры",
};
export const productTabs = [
  { id: "general", label: "Основные" },
  { id: "inventory", label: "Наличие" },
  { id: "shipping", label: "Доставка" },
] as const;
export function safeProductHtml(value: string | null | undefined): string {
  return DOMPurify.sanitize(value ?? "", {
    ALLOWED_TAGS: [
      "p",
      "br",
      "strong",
      "em",
      "b",
      "i",
      "ul",
      "ol",
      "li",
      "blockquote",
      "a",
      "h2",
      "h3",
      "code",
      "pre",
    ],
    ALLOWED_ATTR: ["href", "title"],
    ALLOW_DATA_ATTR: false,
  });
}
export function productPrice(item: CatalogItem): string {
  return item.price === null
    ? "Не задано"
    : `${item.price} ${item.price_specification?.currency ?? ""}`.trim();
}
export function overviewModel(
  item: CatalogItem,
  imageUrl: (imageId: string) => string,
): ProductOverviewModel {
  const unitLabels: Record<string, string> = {
    g: "г",
    kg: "кг",
    cm: "см",
    m: "м",
  };
  const measurements = [
    { label: "Вес", measurement: item.weight },
    ...(["length", "width", "height"] as const).map((key, index) => ({
      label: ["Длина", "Ширина", "Высота"][index]!,
      measurement: item.dimensions?.[key],
    })),
  ].map((v) => ({
    label: v.label,
    value: v.measurement
      ? `${v.measurement.value} ${unitLabels[v.measurement.unit]}`
      : "Не задано",
  }));
  return {
    title: item.title ?? "Товар без названия",
    status: statusLabels[item.status]!,
    sku: item.sku,
    price: productPrice(item),
    stock: stockLabels[item.stock_status ?? ""] ?? "Не задано",
    available: item.available_for_sale,
    body: safeProductHtml(item.content?.body),
    images: (item.gallery?.images ?? []).map((v) => ({
      ...v,
      url: imageUrl(v.id),
    })),
    primaryImage: item.gallery?.primary_image_id ?? null,
    measurements,
    quantity: item.stock.manage_stock ? item.stock.stock_quantity : null,
  };
}
