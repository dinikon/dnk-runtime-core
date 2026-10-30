import { ChannelApiError } from "./channel.types";
const messages: Record<string, string> = {
  feed_source_url_invalid:
    "Укажите публичную HTTPS-ссылку исходного XML без перенаправлений.",
  feed_source_unavailable:
    "Не удалось получить исходный XML. Проверьте ссылку и доступность источника.",
  feed_public_origin_unavailable:
    "Для фида и изображений нужен настроенный публичный HTTPS-адрес API.",
  feed_connection_unverified: "Сначала проверьте подключение Prom.",
  feed_import_disabled: "Сначала включите выдачу проверенного XML-фида.",
  feed_import_active:
    "Предыдущий импорт ещё не завершён или его результат требует выяснения.",
  feed_delivery_revision_conflict:
    "Состояние импорта изменилось. Актуальные данные загружены — проверьте их перед действием.",
  feed_revision_conflict:
    "Настройки фида изменились. Ваш ввод сохранён; сверяйте его с актуальной версией.",
  feed_import_acceptance_unknown:
    "Prom мог принять ссылку. Повторная отправка остановлена. Найдите импорт в кабинете Prom и укажите его ID.",
  feed_import_rejected:
    "Prom отклонил запрос импорта. Проверьте доступ и параметры перед новым запуском.",
  feed_import_would_create_product:
    "В исходном XML есть ключи, не подтверждённые в этом магазине. Импорт остановлен, чтобы не создать товары.",
  feed_import_unmatched_content_changed:
    "Исходный XML содержит устаревший контент несопоставленных позиций. Обновите источник перед импортом.",
  feed_import_identity_changed:
    "Ключи импорта больше не соответствуют этому магазину или публикациям. Повторите синхронизацию.",
  feed_import_key_missing:
    "У публикации нет подтверждённого ключа импорта. Повторите синхронизацию Prom.",
  feed_import_key_duplicate:
    "Ключ импорта неоднозначен. Устраните дубли перед запуском.",
  feed_import_no_targets:
    "В фиде нет сопоставленных позиций с разрешённым экспортом контента.",
  feed_import_tracking_expired:
    "Автоматическое наблюдение приостановлено. Можно продолжить проверку того же ID без повторного импорта.",
  feed_import_context_changed:
    "Контент или настройки изменились во время операции. Актуальная версия требует новой проверки.",
  feed_import_content_unconfirmed:
    "Часть полей не подтверждена. Сравните наблюдаемую публикацию с представлением.",
  feed_import_report_requires_attention:
    "Отчёт Prom содержит ошибки, неполные данные или созданные позиции. Проверьте результат.",
  feed_import_id_not_verified:
    "Итоговый отчёт по этому ID пока недоступен. Проверьте ID в кабинете Prom и дождитесь завершения.",
  feed_import_report_pending: "Ожидаем итоговый отчёт Prom.",
  feed_import_report_unavailable:
    "Отчёт временно недоступен. Проверка того же ID продолжится автоматически.",
  feed_import_report_unrecognized:
    "Ответ Prom пока не содержит распознанного итогового отчёта.",
  feed_import_access_denied:
    "Проверка остановлена: у сохранённого доступа недостаточно прав.",
  feed_import_dependencies_unavailable:
    "Операция остановлена из-за недоступного доступа, шифрования или файлов. После исправления проверьте состояние.",
  feed_access_denied: "Недостаточно прав для запуска или проверки импорта.",
  feed_file_forbidden: "Нет права использовать одно из выбранных изображений.",
  feed_source_empty: "Исходный XML пуст. Фид не будет выдан.",
  feed_xml_invalid: "XML повреждён или содержит недопустимые конструкции.",
  feed_import_key_duplicate_source: "В исходном XML есть повторяющиеся ключи.",
  feed_offer_missing: "Экспортируемая позиция отсутствует в исходном XML.",
  feed_format_unsupported:
    "Источник должен соответствовать поддерживаемому формату Prom YML.",
  feed_uk_content_incomplete:
    "Для украинского перевода нужны и название, и описание.",
  feed_gallery_locale_conflict:
    "Prom использует одну галерею: набор изображений по языкам должен совпадать.",
  feed_gallery_clear_unsupported:
    "Очистка всей галереи через этот XML-профиль не поддерживается.",
  feed_description_clear_unsupported:
    "Очистка описания через этот XML-профиль не поддерживается.",
};
export function contentFeedIssue(code: string): string {
  return (
    messages[code] ??
    "Операция не выполнена. Проверьте состояние фида и результат Prom перед повторным действием."
  );
}
export function contentFeedError(error: unknown): string {
  return contentFeedIssue(
    error instanceof ChannelApiError
      ? error.code
      : typeof error === "string"
        ? error
        : "request_failed",
  );
}
