import { FeedApiError } from "./feed.types.ts";
import { SchemaApiError } from "./feed-schema.types.ts";
export function calculationErrorMessage(error: unknown): string {
  if (!error) return "";
  if (error instanceof SchemaApiError && error.status === 422)
    return (
      "Проверьте формулу: " +
      (error.issues.map((i) => i.message).join("; ") || "неверная настройка")
    );
  const status = error instanceof FeedApiError ? error.status : undefined;
  if (status === 401) return "Сессия завершена. Войдите снова.";
  if (status === 403)
    return "Недостаточно прав на предпросмотр или данные каталога.";
  if (status === 404)
    return "Фид, товар или вариант недоступен. Обновите выбор.";
  if (status === 409)
    return "Feed изменён или архивирован. Черновик сохранён; загрузите актуальную схему.";
  if (status === 413) return "Формула превышает допустимый размер.";
  if (status === 503)
    return "Каталог временно недоступен. Повторите расчёт позже.";
  return "Не удалось рассчитать цену. Проверьте настройки поля и повторите запрос.";
}
