import type { DataTableColumn } from "@/components/custom-ui/data-table";
export type ItemPackagingColumn =
  "code" | "name" | "contentQuantity" | "contentUom" | "actions";
export const itemPackagingsColumns: readonly DataTableColumn<ItemPackagingColumn>[] =
  [
    { key: "code", label: "Код", width: 200, pinned: "start" },
    { key: "name", label: "Название", width: 300, grow: true },
    {
      key: "contentQuantity",
      label: "Количество содержимого",
      width: 220,
      align: "right",
    },
    { key: "contentUom", label: "Единица", width: 130 },
    { key: "actions", label: "Действия", width: 170 },
  ];
