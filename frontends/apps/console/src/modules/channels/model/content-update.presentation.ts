import type { ContentUpdate } from "./content-update.types";
export const contentUpdateLabels: Record<string, string> = {
  preparing: "Получаем тексты площадки",
  ready: "Готово к обновлению",
  blocked: "Обновление недоступно",
  queued: "В очереди",
  running: "Обновляем и проверяем",
  succeeded: "Обновление подтверждено",
  partial: "Обновлено частично",
  failed: "Не удалось подтвердить обновление",
  stale: "Данные изменились",
  preview_pending: "Ожидает сравнения",
  unchanged: "Тексты совпадают",
  pending: "Ожидает отправки",
  sending: "Отправляем",
  verifying: "Проверяем результат",
  reconciling: "Сверяем результат",
  unknown: "Результат отправки неизвестен",
};
export function contentUpdateActive(run: ContentUpdate | undefined): boolean {
  return (
    !!run &&
    !run.interrupted &&
    ["preparing", "queued", "running"].includes(run.status)
  );
}
export function contentUpdateLabel(run: ContentUpdate): string {
  if (
    run.status === "ready" &&
    run.items.every((item) => item.status === "unchanged")
  )
    return "Тексты уже совпадают";
  return contentUpdateLabels[run.status] ?? run.status;
}
export function canConfirmContentUpdate(
  run: ContentUpdate,
  now = Date.now(),
): boolean {
  return (
    run.status === "ready" &&
    run.outboundEnabled &&
    !run.confirmedAt &&
    !!run.previewHash &&
    Date.parse(run.expiresAt) > now &&
    run.items.some((item) => item.status === "ready")
  );
}
