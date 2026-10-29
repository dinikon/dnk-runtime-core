import type { DataTableColumn } from "@/components/custom-ui/data-table";

export type BindingGroupsColumn =
  | "publication"
  | "channel"
  | "catalog"
  | "mode"
  | "state"
  | "matched"
  | "actions";
export const bindingGroupsColumns: readonly DataTableColumn<BindingGroupsColumn>[] =
  [
    { key: "publication", label: "Публикация", width: 260, pinned: "start" },
    { key: "channel", label: "Канал", width: 180, grow: true },
    { key: "catalog", label: "Товар", width: 220 },
    { key: "mode", label: "Тип связи", width: 240 },
    { key: "state", label: "Состояние", width: 170 },
    { key: "matched", label: "Сопоставлено", width: 140, align: "right" },
    { key: "actions", label: "Действия", width: 56, align: "right" },
  ];
