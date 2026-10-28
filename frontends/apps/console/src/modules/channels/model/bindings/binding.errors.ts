import axios from "axios";
export const bindingIssueLabels: Record<string, string> = {
  binding_items_empty: "Добавьте хотя бы одну пару.",
  binding_catalog_missing: "Карточка Catalog отсутствует.",
  binding_catalog_kind_invalid: "Выбран неподходящий тип Catalog.",
  binding_catalog_position_invalid:
    "Позиция не принадлежит выбранной карточке Catalog.",
  binding_publication_occupied:
    "Публикация или её карточка уже закреплена за другой группой.",
  binding_position_duplicate:
    "Одна позиция не может повторяться внутри группы.",
  binding_publication_not_standalone:
    "Нужен самостоятельный простой товар без разновидностей.",
  binding_publication_root_invalid:
    "Внешняя карточка отсутствует или стала разновидностью.",
  binding_simple_structure_invalid:
    "Выберите самостоятельную простую публикацию.",
  binding_variable_structure_invalid:
    "Нужна карточка с разновидностями Prom или WooCommerce.",
  binding_publication_position_invalid:
    "Публикация больше не принадлежит этой внешней карточке.",
  binding_structure_changed:
    "Структура изменилась. Обновите проверку, ваши пары сохранены в редакторе.",
  binding_revision_conflict:
    "Связь изменена в другом редакторе. Перечитайте её перед сохранением.",
  binding_not_found: "Связь удалена или недоступна.",
  binding_anchors_immutable:
    "Для смены карточки или режима сначала снимите группу.",
  access_denied: "Недостаточно прав на управление связями.",
  request_invalid: "Проверьте выбранные значения и обязательные поля.",
};
export function bindingError(error: unknown): string {
  const code =
    typeof error === "string"
      ? error
      : axios.isAxiosError(error)
        ? error.response?.data?.detail?.code
        : undefined;
  return (
    bindingIssueLabels[String(code)] ??
    "Не удалось выполнить операцию. Обновите данные и повторите попытку."
  );
}

export function bindingCreationUncertain(error: unknown): boolean {
  return (
    !axios.isAxiosError(error) ||
    !error.response ||
    error.response.status >= 500 ||
    error.response.status === 408
  );
}
