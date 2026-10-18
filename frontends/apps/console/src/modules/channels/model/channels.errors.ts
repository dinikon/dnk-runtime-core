import { ChannelsApiError } from "../api/channels.error";
import { reasonLabel } from "./channels.presentation";
export function channelErrorMessage(error: unknown): string {
  if (error instanceof ChannelsApiError) {
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
