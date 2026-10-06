import type { PublicationImportRun } from "./types";
export const importLabels: Record<PublicationImportRun["status"], string> = {
  queued: "Ожидает загрузки",
  running: "Загрузка публикаций",
  succeeded: "Загрузка завершена",
  partial: "Загружена часть публикаций",
  failed: "Не удалось загрузить публикации",
};
const errors: Record<string, string> = {
  access_denied:
    "Платформа отклонила ключи или права доступа. Проверьте настройки подключения.",
  source_unavailable:
    "Платформа временно недоступна. Повторите загрузку позже.",
  connection_changed:
    "Подключение изменилось во время загрузки. Запустите загрузку заново.",
  channel_inactive: "Канал выключен. Включите его в настройках подключения.",
  worker_exhausted: "Фоновое задание не завершилось. Повторите загрузку.",
  secrets_unavailable:
    "Хранилище ключей недоступно. Обратитесь к администратору.",
};
export function importError(code: string | null) {
  return code
    ? (errors[code] ??
        "Источник вернул неподходящие данные. Повторите загрузку или проверьте подключение.")
    : "";
}
const sourceLabels: Record<string, string> = {
  publish: "Опубликован",
  draft: "Черновик",
  pending: "Ожидает публикации",
  private: "Приватный",
  on_display: "Опубликован",
  not_on_display: "Скрыт",
  deleted: "Удалён",
  editing_required: "Требует редактирования",
  approval_pending: "На модерации",
  deleted_by_moderator: "Удалён модератором",
  instock: "В наличии",
  outofstock: "Нет в наличии",
  onbackorder: "Под заказ",
  available: "В наличии",
  not_available: "Нет в наличии",
  order: "Под заказ",
  service: "Услуга",
};
export function sourceLabel(value: string | null) {
  return value ? (sourceLabels[value] ?? value) : "Нет данных";
}
export function priceLabel(value: string | null, currency: string | null) {
  return value === null
    ? "Нет данных"
    : `${value}${currency ? " " + currency : " (валюта не указана)"}`;
}
export function dateLabel(value: string) {
  return new Date(value).toLocaleString("ru-RU");
}
