import type { DataTableColumn } from "@/components/custom-ui/data-table";

export type InventoryItemColumn =
  | "sku"
  | "baseUom"
  | "quantityStep"
  | "trackingMode"
  | "expirationMode"
  | "actions";

export const inventoryItemsColumns: readonly DataTableColumn<InventoryItemColumn>[] =
  [
    { key: "sku", label: "SKU", width: 240, pinned: "start" },
    { key: "baseUom", label: "Базовая единица", width: 160 },
    {
      key: "quantityStep",
      label: "Шаг количества",
      width: 200,
      align: "right",
    },
    { key: "trackingMode", label: "Прослеживаемость", width: 230, grow: true },
    { key: "expirationMode", label: "Учёт срока годности", width: 240 },
    { key: "actions", label: "Действия", width: 290 },
  ];
