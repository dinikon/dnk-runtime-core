import type { DataTableColumn } from "@/components/custom-ui/data-table";

export type CatalogItemsColumn =
  "title" | "sku" | "kind" | "status" | "price" | "stock" | "actions";

export const catalogItemsColumns: readonly DataTableColumn<CatalogItemsColumn>[] =
  [
    { key: "title", label: "Товар", width: 320, pinned: "start" },
    { key: "sku", label: "SKU", width: 130, grow: true },
    { key: "kind", label: "Тип", width: 150 },
    { key: "status", label: "Статус", width: 120 },
    { key: "price", label: "Цена", width: 240, align: "right" },
    { key: "stock", label: "Остаток", width: 180, align: "right" },
    { key: "actions", label: "Действия", width: 56, align: "right" },
  ];
