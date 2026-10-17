import type { ProductSection, ProductTab } from "./product.types";

export const editorGroups = [
  {
    id: "identity",
    title: "Основные сведения",
    sections: ["content", "sku", "virtual"],
  },
  { id: "pricing", title: "Цена и наличие", sections: ["price", "stock"] },
  { id: "media", title: "Изображения", sections: ["galleries"] },
  { id: "descriptions", title: "Описания", sections: ["content"] },
  {
    id: "classification",
    title: "Категории и метки",
    sections: ["categories", "tags"],
  },
  { id: "attributes", title: "Характеристики", sections: ["attributes"] },
  { id: "measurements", title: "Вес и размеры", sections: ["measurements"] },
  { id: "metadata", title: "Дополнительные поля", sections: ["metadata"] },
] as const satisfies readonly {
  id: string;
  title: string;
  sections: readonly ProductSection[];
}[];
export type EditorGroup = (typeof editorGroups)[number]["id"];
export const tabGroup: Record<ProductTab, EditorGroup> = {
  general: "identity",
  inventory: "pricing",
  shipping: "measurements",
  attributes: "attributes",
  additional: "metadata",
};
