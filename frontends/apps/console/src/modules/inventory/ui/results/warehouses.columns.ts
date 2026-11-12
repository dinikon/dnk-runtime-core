import type { DataTableColumn } from "@/components/custom-ui/data-table";
export type WarehouseColumn = "code" | "name" | "isActive" | "actions";
export const warehousesColumns: readonly DataTableColumn<WarehouseColumn>[] = [
  { key: "code", label: "Код", width: 220, pinned: "start" },
  { key: "name", label: "Название", width: 320, grow: true },
  { key: "isActive", label: "Активность", width: 180 },
  { key: "actions", label: "Действия", width: 170 },
];
