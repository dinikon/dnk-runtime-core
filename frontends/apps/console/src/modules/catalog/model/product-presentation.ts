import DOMPurify from "dompurify";
import type {
  CatalogAttribute,
  CatalogCategory,
  CatalogItem,
  CatalogTag,
} from "./catalog.types";
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
  metadata: "Дополнительные поля",
  attributes: "Общие характеристики",
};
export const saveLabels: Record<string, string> = {
  content: "Сохранить тексты",
  status: "Сохранить статус",
  sku: "Сохранить артикул",
  virtual: "Сохранить виртуальность",
  price: "Сохранить цену",
  stock: "Сохранить наличие",
  measurements: "Сохранить измерения",
  metadata: "Сохранить дополнительные поля",
  attributes: "Сохранить характеристики",
};
export const productTabs = [
  { id: "general", label: "Основные" },
  { id: "inventory", label: "Наличие" },
  { id: "shipping", label: "Доставка" },
  { id: "attributes", label: "Характеристики" },
  { id: "additional", label: "Дополнительно" },
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
  attributes: CatalogAttribute[],
  categories: CatalogCategory[],
  tags: CatalogTag[],
  imageUrl: (itemId: string, imageId: string) => string,
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
    descriptions: {
      short: safeProductHtml(item.content?.short_desc),
      full: safeProductHtml(item.content?.desc),
    },
    images: (item.gallery?.images ?? []).map((v) => ({
      ...v,
      url: imageUrl(item.id, v.id),
    })),
    primaryImage: item.gallery?.primary_image_id ?? null,
    measurements,
    attributes: item.attributes.map((v) => {
      const a = attributes.find((a) => a.id === v.attribute_id);
      return {
        label: a?.label ?? a?.code ?? "Характеристика",
        value:
          v.option_ids
            .map(
              (o) =>
                a?.options.find((v) => v.id === o)?.label ??
                a?.options.find((v) => v.id === o)?.code ??
                "Не задано",
            )
            .join(", ") || "Не задано",
      };
    }),
    categories: item.category_ids.map(
      (id) => categories.find((v) => v.id === id)?.label ?? "Без перевода",
    ),
    tags: item.tag_ids.map(
      (id) => tags.find((v) => v.id === id)?.label ?? "Без перевода",
    ),
    quantity: item.stock.manage_stock ? item.stock.stock_quantity : null,
  };
}
