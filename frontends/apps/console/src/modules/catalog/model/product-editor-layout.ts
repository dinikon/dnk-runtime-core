import type { ProductSection } from "./product.types";

export const editorGroups = [
  { id: "status", title: "Статус", sections: ["status"] },
  {
    id: "identity",
    title: "Основные сведения",
    sections: ["content", "sku", "virtual"],
  },
  { id: "categories", title: "Категории", sections: ["categories"] },
  { id: "pricing", title: "Цены", sections: ["price", "purchase_price"] },
  { id: "stock", title: "Наличие", sections: ["stock"] },
  { id: "descriptions", title: "Описание", sections: ["content"] },
  { id: "measurements", title: "Вес и размеры", sections: ["measurements"] },
  { id: "media", title: "Галерея", sections: ["galleries"] },
] as const satisfies readonly {
  id: string;
  title: string;
  sections: readonly ProductSection[];
}[];
export type EditorGroup = (typeof editorGroups)[number]["id"];
