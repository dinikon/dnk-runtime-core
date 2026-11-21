import type {
  InternalMovesParams,
  InternalMoveStatus,
} from "./internal-move.types.ts";
export const internalMoveStatuses: readonly InternalMoveStatus[] = [
  "DRAFT",
  "CONFIRMED",
  "PARTIALLY_EXECUTED",
  "COMPLETED",
  "CANCELLED",
];
export const internalMoveStatusLabels: Record<InternalMoveStatus, string> = {
  DRAFT: "Черновик",
  CONFIRMED: "Подтверждён",
  PARTIALLY_EXECUTED: "Частично выполнен",
  COMPLETED: "Выполнен",
  CANCELLED: "Отменён",
};
export function parseInternalMovePage(
  query: Record<string, unknown>,
): InternalMovesParams {
  const text = (v: unknown): string => (typeof v === "string" ? v : "");
  const status = text(query.status);
  return {
    search: text(query.search),
    warehouseId: text(query.warehouse_id) || undefined,
    ownerId: text(query.owner_id) || undefined,
    status:
      status === "ALL"
        ? "ALL"
        : internalMoveStatuses.includes(status as InternalMoveStatus)
          ? (status as InternalMoveStatus)
          : "DRAFT",
    createdFrom: text(query.created_from) || undefined,
    createdTo: text(query.created_to) || undefined,
    offset: Math.max(0, Number.parseInt(text(query.offset), 10) || 0),
    limit: 20,
  };
}
export function internalMovePageQuery(
  p: InternalMovesParams,
): Record<string, string | undefined> {
  return {
    search: p.search || undefined,
    warehouse_id: p.warehouseId,
    owner_id: p.ownerId,
    status: p.status === "DRAFT" ? undefined : p.status,
    created_from: p.createdFrom,
    created_to: p.createdTo,
    offset: p.offset ? String(p.offset) : undefined,
  };
}
