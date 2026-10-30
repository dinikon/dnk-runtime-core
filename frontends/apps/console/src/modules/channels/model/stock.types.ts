export type StockDirection = "read" | "write";
export type StockStatus =
  "queued" | "running" | "completed" | "failed" | "cancelled";
export interface StockOperation {
  id: string;
  direction: StockDirection;
  status: StockStatus;
  observedAt: string | null;
  desiredQuantity: number | null;
  errorCode: string | null;
  recoveryRequired: boolean;
}
export interface BindingStockItem {
  publicationId: string;
  ownerId: string;
  catalogPositionId: string;
  catalogOwnerId: string;
  catalogQuantity: number | null;
  publicationQuantity: string | null;
  publicationAvailability: string | null;
  exportBlocker: string | null;
  operation: StockOperation | null;
}
export interface BindingStock {
  allowStockExport: boolean;
  items: BindingStockItem[];
}
export interface StockRequest {
  channelId: string;
  groupId: string;
  publicationIds: string[];
}
export const stockStatuses: Record<StockStatus, string> = {
  queued: "В очереди",
  running: "Выполняется",
  completed: "Завершено",
  failed: "Ошибка",
  cancelled: "Отменено",
};
export function stockActive(value: BindingStock | undefined): boolean {
  return (
    value?.items.some(
      (v) =>
        v.operation?.status === "queued" || v.operation?.status === "running",
    ) ?? false
  );
}
