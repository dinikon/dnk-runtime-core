import type { ReturnsParams, ReturnStatus } from "./return.types.ts";
export const returnStatuses: readonly ReturnStatus[] = [
  "DRAFT",
  "CONFIRMED",
  "PARTIALLY_EXECUTED",
  "COMPLETED",
  "CANCELLED",
];
export const returnStatusLabels: Record<ReturnStatus, string> = {
  DRAFT: "Черновик",
  CONFIRMED: "Подтверждён",
  PARTIALLY_EXECUTED: "Частично выполнен",
  COMPLETED: "Выполнен",
  CANCELLED: "Отменён",
};
export function parseReturnPage(query: Record<string, unknown>): ReturnsParams {
  const text = (v: unknown): string => (typeof v === "string" ? v : "");
  const status = text(query.status);
  return {
    search: text(query.search),
    originExecutionId: text(query.origin_execution_id) || undefined,
    warehouseId: text(query.warehouse_id) || undefined,
    ownerId: text(query.owner_id) || undefined,
    status:
      status === "ALL"
        ? "ALL"
        : returnStatuses.includes(status as ReturnStatus)
          ? (status as ReturnStatus)
          : "DRAFT",
    createdFrom: text(query.created_from) || undefined,
    createdTo: text(query.created_to) || undefined,
    offset: Math.max(0, Number.parseInt(text(query.offset), 10) || 0),
    limit: 20,
  };
}
export function returnPageQuery(
  p: ReturnsParams,
): Record<string, string | undefined> {
  return {
    search: p.search || undefined,
    origin_execution_id: p.originExecutionId,
    warehouse_id: p.warehouseId,
    owner_id: p.ownerId,
    status: p.status === "DRAFT" ? undefined : p.status,
    created_from: p.createdFrom,
    created_to: p.createdTo,
    offset: p.offset ? String(p.offset) : undefined,
  };
}
