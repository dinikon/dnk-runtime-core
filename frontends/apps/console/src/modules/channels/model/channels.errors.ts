import { ChannelsApiError } from "../api/channels.error";
import { reasonLabel } from "./channels.presentation";
export function channelErrorMessage(error: unknown): string {
  if (error instanceof ChannelsApiError) {
    if (
      error.code.startsWith("content_update_") ||
      [
        "catalog_content_missing",
        "catalog_content_changed",
        "catalog_content_unavailable",
        "external_content_changed",
        "outbound_sync_disabled",
        "publication_not_found",
      ].includes(error.code)
    )
      return reasonLabel(error.code);
    if (error.code === "publication_revision_conflict")
      return "Публикация обновилась после preview. Загрузите актуальные данные и подтвердите перенос ещё раз.";
    if (
      [
        "publication_already_bound",
        "catalog_item_already_bound",
        "catalog_item_archived",
        "binding_revision_conflict",
        "idempotency_key_reused",
      ].includes(error.code)
    )
      return reasonLabel(error.code);
    if (error.issues.length)
      return error.issues.map((issue) => issue.message).join(" ");
    if (error.status === 409)
      return "Данные изменились или действие сейчас недоступно. Обновлена актуальная версия; проверьте настройки перед повтором. Введённые значения сохранены.";
    if (error.status === 403) return "Недостаточно прав для этого действия.";
    if (error.status === 404) return "Канал или подключение не найдено.";
    if (error.status === 422)
      return error.code === "request_failed"
        ? "Проверьте обязательные поля, адрес, языки и валюту."
        : reasonLabel(error.code);
    if (error.status === 503)
      return "Подключение временно недоступно. Проверьте настройку сервера или повторите позже.";
  }
  return "Не удалось получить ответ сервера. Проверьте соединение и повторите действие.";
}
