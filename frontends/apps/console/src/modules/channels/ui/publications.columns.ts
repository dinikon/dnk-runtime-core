import type { DataTableColumn } from "@/components/custom-ui/data-table";
export type PublicationsColumn =
  | "publication"
  | "sku"
  | "positions"
  | "price"
  | "stock"
  | "binding"
  | "received"
  | "actions";
export const publicationsColumns: readonly DataTableColumn<PublicationsColumn>[] =
  [
    { key: "publication", label: "Публикация", width: 240, pinned: "start" },
    { key: "sku", label: "Артикул / ID", width: 140 },
    { key: "positions", label: "Позиции", width: 90, align: "right" },
    { key: "price", label: "Стоимость", width: 180, align: "right" },
    { key: "stock", label: "Остаток", width: 170, align: "right" },
    { key: "binding", label: "Связь с каталогом", width: 190, grow: true },
    { key: "received", label: "Получено", width: 180 },
    { key: "actions", label: "Действия", width: 168, pinned: "end" },
  ];
