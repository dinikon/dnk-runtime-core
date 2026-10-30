import type { DataTableColumn } from "@/components/custom-ui/data-table";
export type ChannelsColumn =
  "name" | "platform" | "endpoint" | "status" | "checked" | "actions";
export const channelsColumns: readonly DataTableColumn<ChannelsColumn>[] = [
  { key: "name", label: "Название", width: 220, pinned: "start" },
  { key: "platform", label: "Платформа", width: 150 },
  { key: "endpoint", label: "Адрес магазина", width: 260, grow: true },
  { key: "status", label: "Статус проверки", width: 230 },
  { key: "checked", label: "Последняя проверка", width: 180 },
  { key: "actions", label: "Действия", width: 56, align: "right" },
];
