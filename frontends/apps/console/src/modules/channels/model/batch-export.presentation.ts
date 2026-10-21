import type { BatchExportStatus } from "./batch-export.types";
export const batchStatusLabels: Record<BatchExportStatus, string> = {
  preparing: "Подготовка текстов",
  checking: "Проверка идентификаторов",
  building: "Подготовка файла",
  ready: "Файл подготовлен",
  submitting: "Передача в источник",
  processing: "Обработка в источнике",
  verifying: "Проверка карточек",
  unknown: "Требуется проверка",
  succeeded: "Обновление подтверждено",
  partial: "Выполнено частично",
  failed: "Не выполнено",
  empty: "Нет подходящих публикаций",
  prepared: "XML готов для ручного использования",
};
export const exportItemLabels: Record<string, string> = {
  pending: "Подготовка",
  ready: "Включено в XML",
  skipped: "Пропущено",
  verified: "Подтверждено",
  failed: "Ошибка",
  unknown: "Не подтверждено",
};
const reasons: Record<string, string> = {
  export_identity_missing:
    "Нет ключа XML. Укажите его через XLSX и повторите загрузку публикаций.",
  export_identity_changed: "Ключ XML изменился. Повторите загрузку публикаций.",
  export_identity_conflict:
    "Ключ отсутствует в источнике, дублируется или принадлежит другой карточке.",
  export_visibility_unsupported:
    "В этом срезе обновляются только опубликованные карточки.",
  export_variation_unsupported: "Обновление вариантов пока недоступно.",
  export_category_missing: "Источник не вернул категорию карточки.",
  export_source_changed:
    "Карточка изменилась во время подготовки. Она исключена из файла.",
  export_preserved_fields_changed:
    "После импорта изменились другие поля карточки. Проверьте её в источнике.",
  export_texts_not_confirmed:
    "Новые тексты пока не подтверждены чтением карточки.",
  catalog_content_missing:
    "В каталоге нужны название и описание на каждом языке подключения.",
  batch_export_feed_unconfigured:
    "Не найден активный домен тенанта или не настроена подпись выгрузок.",
  batch_export_requires_public_host:
    "XML доступен локально. Для отправки в источник нужен публичный HTTPS-домен тенанта.",
  batch_export_mode_conflict:
    "У подключения уже выполняется другая выгрузка. Дождитесь её завершения.",
  batch_export_confirmation_timeout:
    "За время наблюдения импорт не подтвердил завершение. Повторите проверку результата.",
  batch_export_submission_unconfirmed:
    "Ответ на отправку не получен. Повторная отправка заблокирована; доступна проверка карточек.",
  batch_export_result_unconfirmed:
    "Часть результатов не подтверждена. Повторите проверку без новой отправки.",
  batch_export_bindings_changed:
    "Связи или разрешения изменились во время подготовки. Запустите новый пакет.",
  provider_request_rejected:
    "Источник отклонил запуск. Проверьте, завершён ли предыдущий импорт.",
  provider_import_failed:
    "Источник сообщил об ошибке импорта. Результаты карточек показаны отдельно.",
  outbound_sync_disabled: "Исходящая синхронизация канала выключена.",
  connection_generation_changed:
    "Настройки подключения изменились. Подготовьте новый пакет.",
};
export function exportReason(code: string): string {
  return (
    reasons[code] ??
    "Операция не подтверждена. Проверьте подключение и повторите проверку."
  );
}
export function batchActive(status: BatchExportStatus): boolean {
  return !["succeeded", "partial", "failed", "empty", "prepared"].includes(
    status,
  );
}
export function batchPolling(status: BatchExportStatus): boolean {
  return batchActive(status) && status !== "unknown";
}

export function scheduleDateLabel(value: string, timezone: string): string {
  try {
    return new Intl.DateTimeFormat("ru-RU", {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: timezone,
    }).format(new Date(value));
  } catch {
    return "Дата запуска недоступна";
  }
}
