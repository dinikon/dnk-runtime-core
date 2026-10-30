import axios from "axios";
import { bindingIssueLabels } from "./bindings/binding.errors";

const labels: Record<string, string> = {
  representation_revision_conflict:
    "Представление изменено в другом редакторе. Перечитайте его перед сохранением.",
  representation_binding_changed:
    "Состав группы изменился. Перечитайте представление перед сохранением.",
  representation_config_changed:
    "Настройки подключения изменились. Перечитайте представление.",
  representation_not_saved: "Сначала сохраните представление.",
  representation_context_required:
    "Обновите данные редактора перед проверкой черновика.",
  representation_connection_unverified:
    "Подключение не проверено для текущих настроек.",
  representation_item_not_in_group:
    "Выбранная пара больше не принадлежит группе.",
  representation_title_invalid:
    "Переопределённое название не может быть пустым.",
  representation_gallery_duplicate:
    "Изображение не должно повторяться в одной галерее.",
  representation_image_unavailable:
    "Одно из изображений удалено, недоступно или не готово к использованию.",
  representation_locale_inactive:
    "Этот язык не настроен для подключения. Можно сохранить прежние значения или сбросить их.",
  representation_targets_empty: "В группе нет целей для экспорта.",
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
