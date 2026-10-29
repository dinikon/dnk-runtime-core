import type { DataTableColumn } from "@/components/custom-ui/data-table";

export type CatalogVariantsColumn =
  "title" | "sku" | "price" | "stock" | "status" | "actions";

export const catalogVariantsColumns: readonly DataTableColumn<CatalogVariantsColumn>[] =
  [
    { key: "title", label: "Вариант", width: 260, pinned: "start" },
    { key: "sku", label: "SKU", width: 150, grow: true },
    { key: "price", label: "Цена", width: 220, align: "right" },
    { key: "stock", label: "Наличие", width: 140 },
    { key: "status", label: "Статус", width: 120 },
    { key: "actions", label: "Действия", width: 56, align: "right" },
  ];
