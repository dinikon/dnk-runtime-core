import DOMPurify from "dompurify";
import type {
  CatalogAttribute,
  CatalogCategory,
  CatalogItem,
  CatalogTag,
} from "./catalog.types";
import type { ProductOverviewModel, VariantRowModel } from "./product.types";
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
export const kindLabels = {
  simple: "Простой товар",
  variable: "Товар с вариантами",
  variant: "Вариант товара",
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
  { id: "variants", label: "Варианты" },
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
export function selectionLabel(
  item: CatalogItem,
  attributes: CatalogAttribute[],
): string {
  return (
    item.own.selection.values
      .map(([a, o]) => {
        const attribute = attributes.find((v) => v.id === a);
        return `${attribute?.label ?? attribute?.code ?? "Характеристика"}: ${attribute?.options.find((v) => v.id === o)?.label ?? attribute?.options.find((v) => v.id === o)?.code ?? "Не задано"}`;
      })
      .join(" / ") || "Вариант товара"
  );
}
export function productPrice(item: CatalogItem): string {
  const currency =
    item.priceCurrency ?? item.effective.price_specification?.currency ?? "";
  if (item.kind === "variable")
    return item.priceMin === null
      ? "Не задано"
      : `${item.priceMin}${item.priceMax !== item.priceMin ? ` — ${item.priceMax}` : ""} ${currency}`.trim();
  return item.effective.price === null
    ? "Не задано"
    : `${item.effective.price} ${currency}`.trim();
}
export function variantRow(
  item: CatalogItem,
  attributes: CatalogAttribute[],
  imageUrl: (itemId: string, imageId: string) => string,
): VariantRowModel {
  const gallery = item.effective.gallery;
  const image =
    gallery?.images.find((v) => v.id === gallery.primary_image_id) ??
    gallery?.images[0];
  return {
    item,
    label: selectionLabel(item, attributes),
    image: image ? imageUrl(item.id, image.id) : null,
    price: productPrice(item),
    stock: stockLabels[item.stockStatus ?? ""] ?? "Не задано",
    status: statusLabels[item.own.status] ?? "Не задано",
  };
}
export function overviewModel(
  item: CatalogItem,
  root: CatalogItem,
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
    { label: "Вес", measurement: item.effective.weight },
    ...(["length", "width", "height"] as const).map((key, index) => ({
      label: ["Длина", "Ширина", "Высота"][index]!,
      measurement: item.effective.dimensions?.[key],
    })),
  ].map((v) => ({
    label: v.label,
    value: v.measurement
      ? `${v.measurement.value} ${unitLabels[v.measurement.unit]}`
      : "Не задано",
  }));
  return {
    title: root.title ?? "Товар без названия",
    kind: kindLabels[root.kind],
    status: statusLabels[root.own.status]!,
    sku: item.own.sku,
    price: productPrice(item),
    stock: stockLabels[item.stockStatus ?? ""] ?? "Не задано",
    available: item.availableForSale,
    descriptions: {
      short: safeProductHtml(item.effective.content?.short_desc),
      full: safeProductHtml(item.effective.content?.desc),
    },
    images: (item.effective.gallery?.images ?? []).map((v) => ({
      ...v,
      url: imageUrl(item.id, v.id),
    })),
    primaryImage: item.effective.gallery?.primary_image_id ?? null,
    measurements,
    attributes: item.effective.attributes.map((v) => {
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
    categories: root.own.category_ids.map(
      (id) => categories.find((v) => v.id === id)?.label ?? "Без перевода",
    ),
    tags: root.own.tag_ids.map(
      (id) => tags.find((v) => v.id === id)?.label ?? "Без перевода",
    ),
    sharedQuantity: root.own.stock.manage_stock
      ? root.own.stock.stock_quantity
      : null,
    sharedSource:
      item.effective.stock_source_id === root.id && item.id !== root.id,
    priceIncomplete: item.priceIncomplete,
  };
}
