import type { DataTableColumn } from "@/components/custom-ui/data-table";
export type StockLocationColumn =
  "code" | "name" | "locationType" | "isActive" | "default" | "actions";
export const stockLocationsColumns: readonly DataTableColumn<StockLocationColumn>[] =
  [
    { key: "code", label: "Код", width: 200, pinned: "start" },
    { key: "name", label: "Название", width: 260, grow: true },
    { key: "locationType", label: "Тип", width: 150 },
    { key: "isActive", label: "Активность", width: 150 },
    { key: "default", label: "Основная", width: 180 },
    { key: "actions", label: "Действия", width: 280 },
  ];
