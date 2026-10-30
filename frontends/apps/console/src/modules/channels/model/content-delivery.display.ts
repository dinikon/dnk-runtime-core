import type {
  ContentDelivery,
  ContentDeliveryStatus,
} from "./content-delivery.types";

export function contentDeliveryStatus(status: ContentDeliveryStatus): string {
  return {
    queued: "В очереди",
    in_flight: "Обновляем",
    succeeded: "Обновлено",
    failed: "Ошибка",
    unknown: "Требуется сверка",
    blocked: "Заблокировано",
    cancelled: "Отменено",
  }[status];
}

export function contentDeliverySummary(items: ContentDelivery[]): string {
  if (!items.length) return "Обновление ещё не запускалось";
  if (items.some((item) => item.status === "unknown" || item.recoveryRequired))
    return "Требуется внимание";
  if (items.some((item) => ["queued", "in_flight"].includes(item.status)))
    return "Обновление выполняется";
  const completed = items.filter((item) => item.status === "succeeded").length;
  if (completed === items.length) return "Все цели обновлены";
  return completed ? "Обновлено частично" : "Обновление не завершено";
}
