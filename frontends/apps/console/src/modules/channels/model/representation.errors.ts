import axios from "axios";
import { bindingIssueLabels } from "./bindings/binding.errors";

const labels: Record<string, string> = {
  representation_family_incomplete:
    "Общий контент карточки требует полного сопоставления семьи.",
  representation_publication_stale:
    "Снимок публикации получен для прежних настроек. Обновите публикации.",
  representation_publication_missing:
    "Публикация отсутствует в локальном снимке.",
  representation_external_id_missing:
    "Внешний идентификатор публикации отсутствует.",
  representation_catalog_missing: "Позиция Catalog больше недоступна.",
  representation_title_missing:
    "В Catalog не заполнено название на этом языке.",
  representation_locales_invalid: "Выбранный язык не настроен для канала.",
  channel_not_found: "Канал удалён или недоступен.",
  access_denied: "Недостаточно прав для просмотра представления.",
};
export function representationIssueMessage(code: string): string {
  return (
    labels[code] ??
    bindingIssueLabels[code] ??
    "Не удалось подготовить контент публикации."
  );
}
export function representationErrorMessage(error: unknown): string {
  const code = axios.isAxiosError(error)
    ? error.response?.data?.detail?.code
    : undefined;
  return typeof code === "string"
    ? representationIssueMessage(code)
    : "Не удалось загрузить представление. Повторите попытку.";
}
