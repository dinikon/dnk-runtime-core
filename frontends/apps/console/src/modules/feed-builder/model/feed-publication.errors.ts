import { FeedApiError } from "./feed.types.ts";
import { FeedRequestError } from "./feed-request-error.ts";
export function publicationErrorMessage(error: unknown): string {
  if (!error) return "";
  if (error instanceof FeedApiError) {
    if (error.status === 409)
      return "Данные изменены или фид находится в архиве. Выбор сохранён. Обновите список и повторите действие.";
    if (error.status === 404)
      return "Фид или выбранная позиция недоступны. Проверьте выбор.";
    if (error.status === 403)
      return "Недостаточно прав для управления составом или чтения Catalog.";
    if (error.status === 503)
      return "Каталог временно недоступен. Повторите позже.";
    if (error.status === 422 && error instanceof FeedRequestError)
      return (
        error.issues.map((i) => i.message).join("; ") ||
        "Проверьте выбранные позиции."
      );
  }
  return "Не удалось подтвердить действие. Проверьте состав фида перед повтором.";
}
export function publicationStatusLabel(value: string): string {
  return (
    (
      {
        ENABLED: "Участвует",
        PAUSED: "Приостановлен",
        ARCHIVED: "В архиве",
        DRAFT: "Черновик",
      } as Record<string, string>
    )[value] ?? value
  );
}
