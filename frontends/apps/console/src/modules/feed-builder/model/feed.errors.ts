import { FeedApiError } from "./feed.types.ts";
export function feedErrorMessage(error: unknown, creating = false): string {
  const status = error instanceof FeedApiError ? error.status : undefined;
  if (status === 403) return "Недостаточно прав для этого действия.";
  if (status === 401) return "Сессия завершена. Войдите снова.";
  if (status === 404) return "Фид не найден или недоступен.";
  if (status === 409)
    return creating
      ? "Этот код уже занят, в том числе он может принадлежать архивному фиду. Укажите другой код."
      : "Фид изменён другим пользователем, архивирован или код уже занят. Ваш ввод сохранён. Сверьте данные; для новой версии загрузите актуальные настройки.";
  if (status === 422)
    return "Проверьте название, код и настройки выбранного формата.";
  return creating
    ? "Не удалось подтвердить создание. Фид мог сохраниться. Проверьте список перед созданием нового фида."
    : "Не удалось выполнить запрос. Проверьте актуальное состояние фида перед повтором.";
}
export function isUncertainCreate(error: unknown): boolean {
  return (
    !(error instanceof FeedApiError) ||
    error.status === undefined ||
    error.status >= 500
  );
}
